import os
import threading
from PIL import Image
import numpy as np
from .utils import to_even, to_odd
from . import binary_utils
from . import utils

SIGNATURE_TEXT = utils.envs["STEG_SIGNATURE_TEXT"]
PREFIX_TEXT = utils.envs["STEG_PREFIX_TEXT"]

DEFAULT_COLOR = (0, 0, 0)


def hide_data(img: Image.Image, message: str, key: str, enc_tup: tuple, cb_list:list['function'], cb_args:list[list]) -> Image.Image:
    """
    takes an image , message and key, enc_tup, encrypts the message and stores it in image, returns the stego-image

    :param img: PIL.Image.Image object to embed the text in
    :param message: string of message
    :param key: encryption key as raw text taken from tkinter window input
    :param enc_tup: tuple to show what kind of security is used in embedding text into image
    :return: PIL.Image.Image : stego image - Image which is having data hidden in it
    :raises OverflowError : if the text is too long to embed in given image
    """
    cb1,cb2 = cb_list
    args1,args2 = cb_args
    th1 = threading.Thread(target=cb1,args=args1)
    th2 = threading.Thread(target=cb2,args=args2)
    img = img.convert(mode="RGB") if img.mode != "RGB" else img
    e_key = utils.get_key(key)
    key = utils.get_compact_key(key)[1:-1]
    orientation = utils.randint(0, 1)
    width, height = img.size
    ignored_pixel = (0, 0)  # because this pixel is reserved for metadata
    # putting the encryption method tuple containing orientation as first pixel (0,0)
    tup = list(enc_tup)
    tup.insert(0, orientation)
    enc_tup = tuple(tup)
    # Start of process
    th1.start()
    put_enc_tup(img, enc_tup)
    # Add signature text after encryption to detect the key while extracting the data from image
    message = f"{SIGNATURE_TEXT} {message} {SIGNATURE_TEXT}"
    e_msg = utils.ciph(message, e_key)
    # prefixing with prefix text after encrypting text to test the encoding
    e_msg = f"{PREFIX_TEXT}{e_msg}"
    required_pixels = 1
    if enc_tup[1] == 0:
        required_pixels += 3 * (len(e_msg) + len(key))
    else:
        required_pixels += 3 * len(e_msg)

    if required_pixels > (height * width):
        # given image is not sufficient to store the amount of data provided
        raise OverflowError("Text too long to embed in given image, reduce the length of your text or choose an image which is larger")

    i, j = (0, 0)
    # temp variables for i,j to remember the last known co-ordinates
    ti, tj = (None, None)
    if enc_tup[1] == 0:
        # Include the key in image.
        tempkey = key
        dict3pix = {}
        if orientation == 0:
            while i < width and len(tempkey) != 0:
                while j < height and len(tempkey) != 0:
                    pxl = (i, j)
                    if pxl != ignored_pixel:
                        # store pixel co-ordinates and rgb as key,value in dictionary to later use this dict to put modified pixels
                        dict3pix[pxl] = img.getpixel(pxl)
                        ti, tj = i, j
                        if len(dict3pix.keys()) == 3:
                            # 1 character is ready to be placed in the image
                            char = tempkey[0]
                            stop = len(tempkey) == 1
                            put_char(img, dict3pix, char, stop)
                            tempkey = tempkey[1:]
                            # resetting the dictionary for next character
                            dict3pix = {}
                    j += 1
                i += 1
                j = 0
        else:
            while i < height and len(tempkey) != 0:
                while j < width and len(tempkey) != 0:
                    pxl = (j, i)
                    if pxl != ignored_pixel:
                        dict3pix[pxl] = img.getpixel(pxl)
                        ti, tj = i, j
                        if len(dict3pix.keys()) == 3:
                            char = tempkey[0]
                            stop = len(tempkey) == 1
                            put_char(img, dict3pix, char, stop)
                            tempkey = tempkey[1:]
                            dict3pix = {}
                    j += 1
                i += 1
                j = 0

    # adding the text into image
    (i, j) = (ti, tj) if (ti is not None) else (
    0, 0)  # using the remembered values if key is included, or else starting from (0,0) if key is not included in image
    temptxt = e_msg
    dict3pix = {}
    if orientation == 0:
        while i < width and len(temptxt) != 0:
            while j < height and len(temptxt) != 0:
                pxl = (i, j)
                if pxl != (ti,
                           tj) and pxl != ignored_pixel:  # if current pixel is not the last pixel put while embedding key in image
                    dict3pix[pxl] = img.getpixel(pxl)
                    if len(dict3pix.keys()) == 3:
                        char = temptxt[0]
                        stop = len(temptxt) == 1
                        put_char(img, dict3pix, char, stop)
                        temptxt = temptxt[1:]
                        dict3pix = {}
                j += 1
            i += 1
            j = 0
    else:
        while i < height and len(temptxt) != 0:
            while j < width and len(temptxt) != 0:
                pxl = (j, i)
                if pxl != (tj, ti) and pxl != ignored_pixel:
                    dict3pix[pxl] = img.getpixel(pxl)
                    if len(dict3pix.keys()) == 3:
                        char = temptxt[0]
                        stop = len(temptxt) == 1
                        put_char(img, dict3pix, char, stop)
                        temptxt = temptxt[1:]
                        dict3pix = {}
                j += 1
            i += 1
            j = 0
    # End of process
    th2.start()
    th2.join()
    return img


def extract_data(img: Image.Image, cb_list:list['function'], cb_args:list[list]) -> str:
    """
    Takes an Image object and checks if the given image is encoded using Steganos or not
    if image is not encoded by Steganos, then raises the exception `TypeError`
    else returns the extracted data (string)


    :param img: takes an PIL.Image.Image object
    :return: str : extracted data if image is encoded by Steganos
    :raises TypeError if the given image `img` is not encoded by Steganos tool
    """
    cb1,cb2 = cb_list
    args1,args2 = cb_args
    th1 = threading.Thread(target=cb1,args=args1)
    img = img.convert(mode="RGB") if img.mode != "RGB" else img
    text = ''
    width, height = img.size
    key = None
    ignored_pixel = (0, 0)
    # checking if the encryption tuple is equal to (1,0,1) which is not valid case
    enc_tup = get_enc_tup(img)
    if enc_tup == (1, 0, 1) or enc_tup == (0, 0, 1):
        img.close()
        raise TypeError("Given image is not encoded by Steganos, code 1")

    orientation, sec_level, lvl = enc_tup
    # Start of process
    th1.start()
    i, j = 0, 0
    ti, tj = None, None
    if sec_level == 0:
        key = ''
        stop = False
        pix3list = []
        if orientation == 0:
            while i < width and not stop:
                while j < height and not stop:
                    pxl = (i, j)
                    if pxl != ignored_pixel:
                        pix3list.append(img.getpixel(pxl))
                        ti, tj = i, j
                        if len(pix3list) == 3:
                            char, stop = get_char_data(pix3list)
                            key += char
                            pix3list = []
                    j += 1
                i += 1
                j = 0
        else:
            while i < height and not stop:
                while j < width and not stop:
                    pxl = (j, i)
                    if pxl != ignored_pixel:
                        pix3list.append(img.getpixel(pxl))
                        ti, tj = i, j
                        if len(pix3list) == 3:
                            char, stop = get_char_data(pix3list)
                            key += char
                            pix3list = []
                    j += 1
                i += 1
                j = 0

    i, j = (ti, tj) if (ti is not None) else (
    0, 0)  # using the remembered values if key is included, or else starting from (0,0) if key is not included in image
    stop = False
    rawtxt = ''
    pix3list = []
    if orientation == 0:
        while i < width and not stop:
            while j < height and not stop:
                pxl = (i, j)
                if pxl != (ti, tj) and pxl != ignored_pixel:
                    pix3list.append(img.getpixel(pxl))
                    ti, tj = i, j
                    if len(pix3list) == 3:
                        char, stop = get_char_data(pix3list)
                        rawtxt += char
                        pix3list = []
                j += 1
            i += 1
            j = 0
    else:
        while i < height and not stop:
            while j < width and not stop:
                pxl = (j, i)
                if pxl != (tj, ti) and pxl != ignored_pixel:
                    pix3list.append(img.getpixel(pxl))
                    ti, tj = i, j
                    if len(pix3list) == 3:
                        char, stop = get_char_data(pix3list)
                        rawtxt += char
                        pix3list = []
                j += 1
            i += 1
            j = 0

    pfx = rawtxt[:len(PREFIX_TEXT)]
    if pfx != PREFIX_TEXT:
        img.close()
        raise TypeError("Given image is not encoded by Steganos, code 2")
    # End of process
    text = rawtxt.split(PREFIX_TEXT)[1]
    if key:
        key = utils.get_key(f"[{key}]")
        args2.append({'protected':False})
        th2 = threading.Thread(target=cb2, args=args2)
        th2.start()
        th2.join()
        return utils.deciph(text, key)
    else:
        args2.append({'protected':True})
        th2 = threading.Thread(target=cb2, args=args2)
        th2.start()
        th2.join()
        return text

def get_enc_tup(img: Image.Image) -> tuple:
    """
    takes Image object and returns the encryption strictness tuple
    :param img: PIL.Image.Image
    :return: tuple:  present at encryption strictness pixel i.e (0,0)
    """
    pxl_val = img.getpixel((0, 0))
    return tuple([int(x % 2 != 0) for x in pxl_val])


def put_enc_tup(img: Image.Image, tup: tuple):
    """
    takes image and enc tup and puts it in the image

    :param img: PIL.Image.Image
    :param tup: tuple
    :return: None
    """
    pictup = img.getpixel((0, 0))
    temptup = []
    for i in range(3):
        if tup[i] == 0:
            temptup.append(to_even(pictup[i]))
        else:
            temptup.append(to_odd(pictup[i]))
    img.putpixel((0, 0), tuple(temptup))


def put_char(img: Image.Image, dict3pix: dict, char: str, stop: bool):
    """
    converts char to binary, and embeds it into given 3 pixels in dictionary

    :param img: PIL.Image.Image object to embed the data
    :param dict3pix: dictionary containing co-ordinates of 3 pixels as keys and r,g,b as value
    :param char: str - a single character to put in image
    :param stop: bool to show if the given character is last character of text and to indicate that this is where we have to stop while reading data.
    :return: None
    """
    bchr = binary_utils.text_to_binary(char)[:-1]
    i = 0
    for pxl, data in dict3pix.items():
        temptup = []
        for x in data:
            if i == 8:
                if stop:
                    temptup.append(to_odd(x))
                else:
                    temptup.append(to_even(x))
                break

            if bchr[i] == "0":
                temptup.append(to_even(x))
            else:
                temptup.append(to_odd(x))
            i += 1
        img.putpixel(pxl, tuple(temptup))


def get_char_data(pix3list: list) -> tuple[str, bool]:
    """
    Takes a list containing rgb values of 3 pixels and returns the character embedded in pixels
    and boolean whether to stop extracting data or not

    :param img: PIL.Image.Image
    :param dict3pix: dict : where pixel co-ordinates and rgb are stored as key, value
    :return: tuple[str, bool] : extracted character (str) and stop flag (bool)
    """
    char = ''
    for val in pix3list:
        for i in val:
            char += str(int(i % 2 != 0))
    stop = bool(int(char[-1]))
    char = char[:8]
    char = binary_utils.binary_to_text(char)
    return char, stop


def resizer(img: Image.Image, max_size: int) -> Image.Image:
    """
    Takes the image and resizes it according the max_size provided while keeping the aspect ratio same as original image.

    :param img: PIL.Image.Image
    :param max_size: int
    :return: PIL.Image.Image - Resized image
    """
    width, height = img.size
    multiplier = max_size / max(width, height)
    new_size = int(multiplier * width), int(multiplier * height)
    return img.resize(new_size)


def get_resized_dimensions(img: Image.Image, max_size: int) -> tuple[int]:
    """
    takes Image, returns the modified size tuple

    :param img: PIL.Image.Image
    :return: tuple[int] : size tuple of image
    """
    stup = list(img.size)
    for i in range(len(stup)):
        if stup[i] > max_size:
            stup[i] = max_size
    return tuple(stup)

def save_after(action, action_args, thr_to_join:threading.Thread, job:"django.db.models.Model", fpaths:dict, tpaths:dict):
    thr_to_join.join()
    if action== 'encrypt':
        tipath = tpaths["img"]
        fipath = fpaths["img"]
        ttpath = tpaths["txt"]
        stg_txt = utils.read_bytes(ttpath)
        img = Image.open(tipath)
        action_args.insert(0, img)
        action_args.insert(1,stg_txt)
        try:
            img = hide_data(*action_args)
            img.save(fipath,format="PNG")
            job.result_saved = True
            job.save()
        except OverflowError as err:
            j_errs = job.errs.copy()
            j_errs["OverflowError"] = err.args[0]
            job.errs = j_errs
            job.save()
        finally:
            os.remove(tipath)
            os.remove(ttpath)
    else:
        tipath = tpaths["img"]
        ftpath = fpaths["txt"]
        img = Image.open(tipath)
        action_args.insert(0,img)
        try:
            etxt = extract_data(*action_args)
            utils.write_bytes(ftpath,etxt)
            job.result_saved = True
            job.save()
        except TypeError as err:
            j_errs = job.errs.copy()
            j_errs["TypeError"] = err.args[0]
            job.errs = j_errs
            job.save()
        finally:
            os.remove(tipath)

legend = \
"""
    Basic structure and legend:

    Top left corner pixel contains orientation and encryption tuple information
    Let's consider (o,a,b)
    o : Orientation of traversal in image to extract data :
        0 : vertical
        1 : horizontal
    (a,b) : Tuple which decides what kind of security is used while encrypting this image :
        (0,0) : Key is included in image, extract the key and text , use key to decrypt the text
        (1,0) : Key is not included in image, user will have to provide key, this key will be used to decrypt the extracted text  
        (1,1) : key is not included in image, user will have to provide key, this key will be used to decrypt the extracted text, but in this case only the correct key will be accepted 
"""
