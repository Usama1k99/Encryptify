"""
Image App Views Configuration
"""
import PIL
import threading
from io import BytesIO
from PIL import Image
from datetime import datetime
from home.models import User
from django.http import HttpResponse, JsonResponse, Http404
from django.core.exceptions import PermissionDenied, BadRequest
from django.core.files.uploadedfile import \
    InMemoryUploadedFile,\
    SimpleUploadedFile,\
    TemporaryUploadedFile
from django.shortcuts import render, redirect, reverse
from encsite.middlewares import update_user_last_active
from .models import ImageJob
from . import imgxor, steganos, picit
from . import utils

formats = ["PNG","JPEG","BMP"]

@update_user_last_active
def index(req):
    uinfo = req.session.get('userinfo')
    # return redirect(f"{reverse('img_encryption')}?some=thing")
    if uinfo:
        params = {
            'userinfo': uinfo.copy()
        }
        return render(req, 'image/ilanding.html', params)
    return render(req, 'image/ilanding.html')

# ------------------------ Form Views ------------------------ #

@update_user_last_active
def encryption(req):
    uinfo = req.session.get('userinfo')
    if not req.session.session_key:
        req.session.save()
        if uinfo:
            req.session['userinfo'] = uinfo
    form = req.POST
    params = {}
    if uinfo:
        params = {
            'userinfo' : uinfo.copy()
        }
    if form:
        imgf = req.FILES.get('imgFile')
        if not imgf:
            params['err'] = 'Select an image file to continue'
            return render(req, 'image/encryption.html', params)
        imgf = utils.memory_to_simple_file(imgf)
        save_job = form.get('save') == 'on'
        operation = form.get('operation')
        key = form.get('key')
        job_name = "encryption"
        session_key = req.session.session_key
        expiry_days = 1
        img : Image.Image = None
        try:
            img = Image.open(imgf.file,formats=formats)
        except PIL.UnidentifiedImageError:
            params['err'] = f"You are supposed to only select static image files of formats {', '.join([x.lower() for x in formats])}."
            values = {'key':key}
            if operation == 'encrypt':
                values['echeck'] = 'checked'
            else:
                values['decheck'] = 'checked'
            params['values'] = values
            return render(req,'image/encryption.html',params)

        img_job = ImageJob(
            name=job_name,
            operation=operation,
            save_job=save_job,
            user_name="",
            user_id=session_key,
        )
        img_job.save()
        file_name = f"{img_job.name}_{img_job.operation}_{img_job.id}.png"
        temp_name = f"temp_{file_name}"
        file_dir = job_name
        full_path = f"image/jobs/{file_dir}/{file_name}"
        temp_path = f"image/jobs/{file_dir}/{temp_name}"
        imsave_thr = threading.Thread(target=img.save,args=[temp_path,"PNG"])
        imsave_thr.start()
        if uinfo:
            user = User.objects.get(id=uinfo['id'])
            img_job.user_name = uinfo['name']
            img_job.user_id = user.id
            if save_job:
                expiry_days = 7
            img_job.save()
            user.image_jobs.add(img_job)
            user.save()
        # Arguments to be passed in thread cb
        inner_args = [
            key,
            [utils.cb_start_job_time,utils.cb_finish_job_time],
            [
                [img_job],
                [img_job,expiry_days]
            ]
        ]
        outer_args = [
            imsave_thr,
            inner_args,
            img_job,
            full_path,
            temp_path
        ]
        if operation == 'encrypt':
            outer_args.insert(0,imgxor.encrypt_image)
        else:
            outer_args.insert(0,imgxor.decrypt_image)
        thr = threading.Thread(target=imgxor.save_after,args=outer_args)
        thr.start()
        url_params = {
            'job_id' : img_job.id
        }
        return redirect('img_enc_serve',**url_params)

    else:
        return render(req, 'image/encryption.html', params)


@update_user_last_active
def steganography(req):
    uinfo = req.session.get('userinfo')
    if not req.session.session_key:
        req.session.save()
        if uinfo:
            req.session['userinfo'] = uinfo
    form = req.POST
    params = {}
    if uinfo:
        params = {
            'userinfo': uinfo.copy()
        }
    if form:
        imgf = req.FILES.get('imgFile')
        if not imgf:
            params['err'] = 'Select an image file to continue'
            return render(req,'image/steganos.html',params)
        imgf = utils.memory_to_simple_file(imgf)
        key = form.get('key')
        operation = form.get('operation')
        stg_text = form.get('text') if operation == 'encrypt' else None
        security = form.get('pass-protected') == 'on'
        save_job = form.get('save') == 'on'
        job_name = "steganos"
        session_key = req.session.session_key
        expiry_days = 1
        img: Image.Image = None
        try:
            img = Image.open(imgf.file, formats=formats)
        except PIL.UnidentifiedImageError:
            params['err'] = f"You are supposed to only select static image files of formats " \
                            f"{', '.join([x.lower() for x in formats])}."
            values = {
                'key': key,
                'text' : stg_text
            }
            if operation == 'encrypt':
                values['echeck'] = 'checked'
            else:
                values['decheck'] = 'checked'
            params['values'] = values
            return render(req, 'image/steganos.html', params)

        if operation == 'encrypt':
            checks = [key,stg_text]
            if any(x == '' for x in checks):
                values = {
                    'key': key,
                    'text': stg_text
                }
                values['echeck'] = 'checked'
                params['values'] = values
                params['err'] = "Please fill all the required fields"
                return render(req,'image/steganos.html',params)

        img_job = ImageJob(
            name=job_name,
            operation=operation,
            save_job=save_job,
            user_name="",
            user_id=session_key,
            protected=security
        )
        img_job.save()
        ifile_name = f"{img_job.name}_{img_job.operation}_{img_job.id}.png"
        itemp_name = f"temp_{ifile_name}"
        ifile_dir = f"{job_name}/stego_images"
        ifull_path = f"image/jobs/{ifile_dir}/{ifile_name}"
        itemp_path = f"image/jobs/{ifile_dir}/{itemp_name}"
        # ---------------------------------------------------------------- #
        tfile_name = f"{img_job.name}_{img_job.operation}_{img_job.id}.txt"
        ttemp_name = f"temp_{tfile_name}"
        tfile_dir = f"{job_name}/stego_texts"
        tfull_path = f"image/jobs/{tfile_dir}/{tfile_name}"
        ttemp_path = f"image/jobs/{tfile_dir}/{ttemp_name}"
        # ---------------------------------------------------------------- #
        fpdict = {
            "img" : ifull_path,
            "txt" : tfull_path
        }
        tpdict = {
            "img" : itemp_path,
            "txt" : ttemp_path
        }
        # ---------------------------------------------------------------- #
        file_storage_thread = None
        if operation=="encrypt":
            thdict = {
                "img" : itemp_path,
                "txt" : ttemp_path
            }
            file_storage_thread = threading.Thread(
                target=utils.steg_helper_thread_enc,
                args=[
                    img,
                    stg_text,
                    thdict
                ]
            )
            file_storage_thread.start()
        else:
            file_storage_thread = threading.Thread(
                target=utils.steg_helper_thread_dec,
                args=[
                    img,
                    itemp_path
                ]
            )
            file_storage_thread.start()

        if uinfo:
            user = User.objects.get(id=uinfo['id'])
            img_job.user_name = uinfo['name']
            img_job.user_id = user.id
            if save_job:
                expiry_days = 7
            img_job.save()
            user.image_jobs.add(img_job)
            user.save()

        if operation == 'encrypt':
            etup = (1,1) if security else (0,0)
            inner_args = [
                key,
                etup,
                [
                    utils.cb_start_job_time,
                    utils.cb_finish_job_time
                ],
                [
                    [img_job],
                    [
                        img_job,
                        expiry_days
                    ]
                ]
            ]
            outer_args = [
                operation,
                inner_args,
                file_storage_thread,
                img_job,
                fpdict,
                tpdict,
            ]
            action_thread = threading.Thread(
                target=steganos.save_after,
                args=outer_args
            )
            action_thread.start()
        else:
            inner_args = [
                [
                    utils.cb_start_job_time,
                    utils.cb_finish_job_time
                ],
                [
                    [img_job],
                    [
                        img_job,
                        expiry_days
                    ]
                ]
            ]
            outer_args = [
                operation,
                inner_args,
                file_storage_thread,
                img_job,
                fpdict,
                tpdict
            ]
            action_thread = threading.Thread(
                target=steganos.save_after,
                args=outer_args
            )
            action_thread.start()
        url_params = {
            'job_id': img_job.id
        }
        return redirect("img_stg_serve",**url_params)
    else:
        return render(req,'image/steganos.html',params)


@update_user_last_active
def picit_view(req):
    uinfo = req.session.get('userinfo')
    if not req.session.session_key:
        req.session.save()
        if uinfo:
            req.session['userinfo'] = uinfo
    form = req.POST
    params = {}
    if uinfo:
        params = {
            'userinfo': uinfo.copy()
        }
    if form:
        imgf = req.FILES.get('imgFile')
        operation = form.get('operation')
        imgf = utils.memory_to_simple_file(imgf) if operation=='decrypt' else None
        key = form.get('key')
        pct_text = form.get('text') if operation=='encrypt' else None
        save_job = form.get('save')=='on'
        job_name = "picit"
        session_key = req.session.session_key
        expiry_days = 1
        img: Image.Image = None
        if operation=='decrypt':
            try:
                if imgf:
                    img = Image.open(imgf.file, formats=formats)
                else:
                    values = {
                        'decheck' : "checked",
                    }
                    params['values'] = values
                    params['err'] = "Please fill all the required fields"
                    return render(req, 'image/picit.html', params)
            except PIL.UnidentifiedImageError:
                params['err'] = f"You are supposed to only select static image files of formats " \
                                f"{', '.join([x.lower() for x in formats])}."
                values = {
                    'key': key,
                    'text': pct_text
                }
                if operation == 'encrypt':
                    values['echeck'] = 'checked'
                else:
                    values['decheck'] = 'checked'
                params['values'] = values
                return render(req, 'image/picit.html', params)

        if operation == 'encrypt':
            checks = [key, pct_text]
            if any(x == '' for x in checks):
                values = {
                    'key': key,
                    'text': pct_text
                }
                values['echeck'] = 'checked'
                params['values'] = values
                params['err'] = "Please fill all the required fields"
                return render(req, 'image/picit.html', params)
        else:
            if not imgf:
                params['err'] = 'Select an image file to continue picit'
                return render(req, 'image/picit.html', params)

        img_job = ImageJob(
            name=job_name,
            operation=operation,
            save_job=save_job,
            user_name="",
            user_id=session_key,
            protected=True
        )
        img_job.save()
        ext = 'txt' if operation=='encrypt' else 'png'
        file_name = f"{img_job.name}_{img_job.operation}_{img_job.id}.{ext}"
        file_dir = f"{job_name}/{operation}"
        full_path = f"image/jobs/{file_dir}/{file_name}"
        temp_name = f"temp_{file_name}"
        temp_path = f"image/jobs/{file_dir}/{temp_name}"
        # ---------------------------------------------------------------- #
        pdict = {
            'path' : full_path,
            'temp' : temp_path
        }
        # ---------------------------------------------------------------- #
        file_storage_thread = None
        if operation == "encrypt":
            file_storage_thread = threading.Thread(
                target=utils.picit_helper_thread_enc,
                args=[
                    pct_text,
                    temp_path
                ]
            )
            file_storage_thread.start()
        else:
            if uinfo and save_job:
                expiry_days = 7
            file_storage_thread = threading.Thread(
                target=utils.picit_helper_thread_dec,
                args=[
                    img,
                    full_path,
                    img_job,
                    expiry_days
                ]
            )
            file_storage_thread.start()

        if uinfo:
            user = User.objects.get(id=uinfo['id'])
            img_job.user_name = uinfo['name']
            img_job.user_id = user.id
            if save_job:
                expiry_days = 7
            img_job.save()
            user.image_jobs.add(img_job)
            user.save()

        if operation == 'encrypt':
            inner_args = [
                key,
                [
                    utils.cb_start_job_time,
                    utils.cb_finish_job_time
                ],
                [
                    [img_job],
                    [
                        img_job,
                        expiry_days
                    ]
                ]
            ]
            outer_args = [
                operation,
                inner_args,
                file_storage_thread,
                img_job,
                pdict,
            ]
            action_thread = threading.Thread(
                target=picit.save_after,
                args=outer_args
            )
            action_thread.start()
        else:
            inner_args = [
                [
                    utils.cb_start_job_time,
                    utils.cb_finish_job_time
                ],
                [
                    [img_job],
                    [
                        img_job,
                        expiry_days
                    ]
                ]
            ]
            outer_args = [
                operation,
                inner_args,
                file_storage_thread,
                img_job,
                pdict,
            ]
            action_thread = threading.Thread(
                target=picit.save_after,
                args=outer_args
            )
            action_thread.start()
        return redirect(f"/image/picit/tasks/{img_job.id}/")
    else:
        return render(req, 'image/picit.html', params)

# ------------------------ Display Views ------------------------ #

@update_user_last_active
def enc_serve(req,job_id):
    uinfo = req.session.get('userinfo')
    params = {
        'title' : f"Image Encryption: {job_id} - Encryptify"
    }
    if uinfo:
        params['userinfo'] = uinfo.copy()

    try:
        job = ImageJob.objects.get(id=job_id,name='encryption')
    except ImageJob.DoesNotExist:
        raise BadRequest("Requested task doesn't exist")
    else:
        if uinfo:
            user = User.objects.get(id=uinfo['id'])
            if job.user_id != user.id:
                raise PermissionDenied("You do not have permission to access this file.")
            params['job_info'] = "Please wait while we process your request"
            params['job_id'] = job_id
            return render(req,"image/serve_enc.html",params)
        else:
            session_key = req.session.session_key
            if job.user_id != session_key:
                raise PermissionDenied("You do not have permission to access this file")
            params['job_info'] = "Please wait while we process your request"
            params['job_id'] = job_id
            return render(req,"image/serve_enc.html",params)


@update_user_last_active
def stg_serve(req,job_id):
    uinfo = req.session.get('userinfo')
    params = {
        'title' : f"Steganos : {job_id} - Encryptify"
    }
    if uinfo:
        params['userinfo'] = uinfo.copy()

    try:
        job = ImageJob.objects.get(id=job_id,name='steganos')
    except ImageJob.DoesNotExist:
        raise BadRequest("Requested task doesn't exist")
    else:
        if uinfo:
            user = User.objects.get(id=uinfo['id'])
            if job.user_id != user.id:
                raise PermissionDenied("You do not have permission to access this file.")
            params['job_info'] = "Please wait while we process your request"
            params['job_id'] = job_id
            return render(req, "image/serve_stg.html", params)
        else:
            session_key = req.session.session_key
            if job.user_id != session_key:
                raise PermissionDenied("You do not have permission to access this file")
            params['job_info'] = "Please wait while we process your request"
            params['job_id'] = job_id
            return render(req, "image/serve_stg.html", params)


@update_user_last_active
def pct_serve(req,job_id):
    uinfo = req.session.get('userinfo')
    params = {
        'title' : f"PicIt : {job_id} - Encryptify"
    }
    if uinfo:
        params['userinfo'] = uinfo.copy()

    try:
        job = ImageJob.objects.get(id=job_id,name='picit')
    except ImageJob.DoesNotExist:
        raise BadRequest("Requested task doesn't exist")
    else:
        if uinfo:
            user = User.objects.get(id=uinfo['id'])
            if job.user_id != user.id:
                raise PermissionDenied("You do not have permission to access this file.")
            params['job_info'] = "Please wait while we process your request"
            params['job_id'] = job_id
            return render(req, "image/serve_pct.html", params)
        else:
            session_key = req.session.session_key
            if job.user_id != session_key:
                raise PermissionDenied("You do not have permission to access this file")
            params['job_info'] = "Please wait while we process your request"
            params['job_id'] = job_id
            return render(req, "image/serve_pct.html", params)

# ------------------------ Job Views ------------------------ #
@update_user_last_active
def enc_attachment(req,job_id):
    uinfo = req.session.get('userinfo')
    params = {}
    if uinfo:
        params = {
            'userinfo' : uinfo.copy()
        }
    try:
        job = ImageJob.objects.get(id=job_id,name='encryption')
    except ImageJob.DoesNotExist: # 400
        return JsonResponse({
            'status' : 400,
            'message' : "Requested job does not exist."
        })
    else:
        if uinfo:
            user = User.objects.get(id=uinfo['id'])
            if job.user_id != user.id: # 403
                return JsonResponse({
                    'status' : 403,
                    'message' : "You do not have permission to access this file."
                })
            if job.status() == "Finished":
                file_dir = "encryption"
                file_name = f"{job.name}_{job.operation}_{job.id}.png"
                full_path = f"image/jobs/{file_dir}/{file_name}"
                try:
                    img = Image.open(full_path)
                    imbytes = BytesIO()
                    img.save(imbytes,format="PNG")
                    response = HttpResponse(imbytes.getvalue(),content_type='image/png')
                    response['Content-Disposition'] = f'attachment; filename="{user.name}_{file_name}"'
                    return response
                except FileNotFoundError:
                    return JsonResponse({
                        'status' : 410,
                        'message' : "Requested file does not exist"
                    })
            else:
                params['job_info'] = "Your task has not been completed yet. Once it is successfully processed on our server, we will promptly update the page with the completed results."
                return JsonResponse({
                    'status' : 102,
                    'message' : params['job_info']
                })
        else:
            session_key = req.session.session_key
            if job.user_id != session_key:
                return JsonResponse({
                    'status': 403,
                    'message': "You do not have permission to access this file."
                })
            if job.status() == "Finished":
                file_dir = "encryption"
                file_name = f"{job.name}_{job.operation}_{job.id}.png"
                full_path = f"image/jobs/{file_dir}/{file_name}"
                try:
                    img = Image.open(full_path)
                    imbytes = BytesIO()
                    img.save(imbytes,format="PNG")
                    response = HttpResponse(imbytes.getvalue(), content_type='image/png')
                    response['Content-Disposition'] = f'attachment; filename="_{file_name}"'
                    return response
                except FileNotFoundError:
                    return JsonResponse({
                        'status': 500,
                        'message': "Requested file does not exist"
                    })
            else:
                params['job_info'] = "Your task has not been completed yet. Once it is successfully processed on our server, we will promptly update the page with the completed results."
                return JsonResponse({
                    'status' : 102,
                    'message' : params['job_info']
                })

@update_user_last_active
def stg_attachment(req,job_id):
    uinfo = req.session.get('userinfo')
    params = {}
    if uinfo:
        params = {
            'userinfo': uinfo.copy()
        }
    try:
        job = ImageJob.objects.get(id=job_id,name='steganos')
    except ImageJob.DoesNotExist:  # 400
        return JsonResponse({
            'status': 400,
            'message': "Requested job does not exist."
        })

    ftype = "img" if job.operation == "encrypt" else "txt"
    if uinfo:
        user = User.objects.get(id=uinfo['id'])
        if job.user_id != user.id:  # 403
            return JsonResponse({
                'status': 403,
                'message': "You do not have permission to access this file."
            })
        if job.status() == "Finished":
            if ftype == "img":
                file_dir = "steganos/stego_images"
                file_name = f"{job.name}_{job.operation}_{job.id}.png"
                full_path = f"image/jobs/{file_dir}/{file_name}"
                try:
                    img = Image.open(full_path)
                    imbytes = BytesIO()
                    img.save(imbytes, format="PNG")
                    response = HttpResponse(imbytes.getvalue(), content_type='image/png')
                    response['Content-Disposition'] = f'attachment; filename="{user.name}_{file_name}"'
                    return response
                except FileNotFoundError:
                    return JsonResponse({
                        'status': 410,
                        'message': "Requested file does not exist"
                    })
            else:
                key = req.GET.get('key','')
                key = utils.get_key(key)
                file_dir = "steganos/stego_texts"
                file_name = f"{job.name}_{job.operation}_{job.id}.txt"
                full_path = f"image/jobs/{file_dir}/{file_name}"
                try:
                    text_data = utils.read_bytes(full_path)
                    if job.protected:
                        if not key:
                            return JsonResponse({
                                'status' : 403,
                                'err' : "The password/encryption key you provided is incorrect"
                            })
                        dec_txt = utils.deciph(text=text_data,key=key)
                        dtxt_list = dec_txt.split(' ')
                        condition = dtxt_list[0] == steganos.SIGNATURE_TEXT and dtxt_list[-1] == steganos.SIGNATURE_TEXT
                        if condition:
                            rtxt = " ".join(dtxt_list[1:-1])
                            return JsonResponse({
                                'status' : 200,
                                'text' : rtxt,
                                'filename' : f"{user.name}_{file_name}"
                            })
                        else:
                            return JsonResponse({
                                'status' : 403,
                                'err' : "The password/encryption key you provided is incorrect"
                            })
                    else:
                        txlist = text_data.split(' ')
                        rtxt = " ".join(txlist[1:-1])
                        return JsonResponse({
                            'status' : 200,
                            'text' : rtxt,
                            'filename' : f"{user.name}_{file_name}"
                        })
                except FileNotFoundError:
                    return JsonResponse({
                        'status' : 410,
                        'err' : 'Requested file does not exist'
                    })
        elif job.status() == 'error':
            return JsonResponse({
                'status': 415,
                'message': "Error",
                'errs': job.errs
            })
        else:
            params['job_info'] = "Your task has not been completed yet. Once it is successfully processed on our server, we will promptly update the page with the completed results."
            return JsonResponse({
                'status': 102,
                'message': params['job_info']
            })
    else:
        session_key = req.session.session_key
        if job.user_id != session_key:
            return JsonResponse({
                'status': 403,
                'message': "You do not have permission to access this file."
            })
        if job.status() == "Finished":
            if ftype == "img":
                file_dir = "steganos/stego_images"
                file_name = f"{job.name}_{job.operation}_{job.id}.png"
                full_path = f"image/jobs/{file_dir}/{file_name}"
                try:
                    img = Image.open(full_path)
                    imbytes = BytesIO()
                    img.save(imbytes, format="PNG")
                    response = HttpResponse(imbytes.getvalue(), content_type='image/png')
                    response['Content-Disposition'] = f'attachment; filename="_{file_name}"'
                    return response
                except FileNotFoundError:
                    return JsonResponse({
                        'status': 500,
                        'message': "Requested file does not exist"
                    })
            else:
                key = req.GET.get('key', '')
                key = utils.get_key(key)
                file_dir = "steganos/stego_texts"
                file_name = f"{job.name}_{job.operation}_{job.id}.txt"
                full_path = f"image/jobs/{file_dir}/{file_name}"
                try:
                    text_data = utils.read_bytes(full_path)
                    if job.protected:
                        if not key:
                            return JsonResponse({
                                'status' : 403,
                                'err' : "The password/encryption key you provided is incorrect"
                            })
                        dec_txt = utils.deciph(text=text_data,key=key)
                        dtxt_list = dec_txt.split(' ')
                        condition = dtxt_list[0] == steganos.SIGNATURE_TEXT and dtxt_list[-1] == steganos.SIGNATURE_TEXT
                        if condition:
                            rtxt = " ".join(dtxt_list[1:-1])
                            return JsonResponse({
                                'status' : 200,
                                'text' : rtxt,
                                'filename' : file_name
                            })
                        else:
                            return JsonResponse({
                                'status' : 403,
                                'message' : "Error",
                                'err' : "The password/encryption key you provided is incorrect"
                            })
                    else:
                        txlist = text_data.split(' ')
                        rtxt = " ".join(txlist[1:-1])
                        return JsonResponse({
                            'status' : 200,
                            'text' : rtxt,
                            'filename' : file_name
                        })
                except FileNotFoundError:
                    return JsonResponse({
                        'status' : 500,
                        'message' : "Error",
                        'err' : 'Requested file does not exist'
                    })
        elif job.status() == 'error':
            return JsonResponse({
                'status' : 415,
                'message' : "Error",
                'errs' : job.errs
            })
        else:
            params['job_info'] = "Your task has not been completed yet. Once it is successfully processed on our server, we will promptly update the page with the completed results."
            return JsonResponse({
                'status': 102,
                'message': params['job_info']
            })

@update_user_last_active
def pct_attachment(req,job_id):
    uinfo = req.session.get('userinfo')
    params = {}
    if uinfo:
        params = {
            'userinfo': uinfo.copy()
        }
    try:
        job = ImageJob.objects.get(id=job_id,name='picit')
    except ImageJob.DoesNotExist:  # 400
        return JsonResponse({
            'status': 400,
            'message': "Requested job does not exist."
        })

    operation = job.operation
    if uinfo:
        user = User.objects.get(id=uinfo['id'])
        if job.user_id != user.id:  # 403
            return JsonResponse({
                'status': 403,
                'message': "You do not have permission to access this file."
            })
        if job.status() == "Finished":
            if operation == "encrypt":
                file_dir = "picit/encrypt"
                file_name = f"{job.name}_{job.operation}_{job.id}.png"
                full_path = f"image/jobs/{file_dir}/{file_name}"
                try:
                    img = Image.open(full_path)
                    imbytes = BytesIO()
                    img.save(imbytes, format="PNG")
                    response = HttpResponse(imbytes.getvalue(), content_type='image/png')
                    response['Content-Disposition'] = f'attachment; filename="{user.name}_{file_name}"'
                    return response
                except FileNotFoundError:
                    return JsonResponse({
                        'status': 410,
                        'message': "Requested file does not exist"
                    })
            else:
                key = req.GET.get('key','')
                key = utils.get_key(key)
                file_dir = "picit/decrypt"
                file_name = f"{job.name}_{job.operation}_{job.id}.png"
                full_path = f"image/jobs/{file_dir}/{file_name}"
                try:
                    img = Image.open(full_path)
                    cb_list = [utils.cb_start_job_time, utils.cb_finish_job_time]
                    cb_args = [
                        [job],
                        [job]
                    ]
                    etext = picit.extract_data(img, key, cb_list, cb_args)
                    etlist = etext.split(' ')
                    signature_text = picit.SIGNATURE_TEXT
                    if etlist[0] == signature_text and etlist[-1] == signature_text:
                        rtext = ' '.join(etlist[1:-1])
                        return JsonResponse({
                            'status': 200,
                            'text': rtext,
                            'filename': utils.set_path_extension(f"{user.name}_{file_name}",'txt'),
                            'job_info' : job.dict()
                        })
                    else:
                        return JsonResponse({
                            'status': 403,
                            'err': "The password/encryption key you provided is incorrect"
                        })
                except Exception as err:
                    if isinstance(err,FileNotFoundError):
                        return JsonResponse({
                            'status' : 410,
                            'err' : 'Requested file does not exist'
                        })
                    elif isinstance(err,TypeError):
                        return JsonResponse({
                            'status' : 415,
                            'message' : "Error",
                            'err' : "The password/encryption key you provided is incorrect"
                        })
        elif job.status() == 'error':
            return JsonResponse({
                'status': 415,
                'message': "Error",
                'errs': job.errs
            })
        else:
            params['job_info'] = "Your task has not been completed yet. Once it is successfully processed on our server, we will promptly update the page with the completed results."
            return JsonResponse({
                'status': 102,
                'message': params['job_info']
            })
    else:
        session_key = req.session.session_key
        if job.user_id != session_key:
            return JsonResponse({
                'status': 403,
                'message': "You do not have permission to access this file."
            })
        if job.status() == "Finished":
            if operation == "encrypt":
                file_dir = "picit/encrypt"
                file_name = f"{job.name}_{job.operation}_{job.id}.png"
                full_path = f"image/jobs/{file_dir}/{file_name}"
                try:
                    img = Image.open(full_path)
                    imbytes = BytesIO()
                    img.save(imbytes, format="PNG")
                    response = HttpResponse(imbytes.getvalue(), content_type='image/png')
                    response['Content-Disposition'] = f'attachment; filename="_{file_name}"'
                    return response
                except FileNotFoundError:
                    return JsonResponse({
                        'status': 500,
                        'message': "Requested file does not exist"
                    })
            else:
                key = req.GET.get('key', '')
                key = utils.get_key(key)
                file_dir = "picit/decrypt"
                file_name = f"{job.name}_{job.operation}_{job.id}.png"
                full_path = f"image/jobs/{file_dir}/{file_name}"
                try:
                    img = Image.open(full_path)
                    cb_list = [utils.cb_start_job_time,utils.cb_finish_job_time]
                    cb_args = [
                        [job],
                        [job]
                    ]
                    etext = picit.extract_data(img,key,cb_list,cb_args)
                    etlist = etext.split(' ')
                    signature_text = picit.SIGNATURE_TEXT
                    if etlist[0] == signature_text and etlist[-1] == signature_text:
                        rtext = ' '.join(etlist[1:-1])
                        return JsonResponse({
                            'status' : 200,
                            'text' : rtext,
                            'filename' : utils.set_path_extension(file_name,'txt'),
                            'job_info' : job.dict()
                        })
                    else:
                        return JsonResponse({
                            'status' : 403,
                            'err' : "The password/encryption key you provided is incorrect"
                        })
                except Exception as err:
                    if isinstance(err, FileNotFoundError):
                        return JsonResponse({
                            'status': 410,
                            'err': 'Requested file does not exist'
                        })
                    elif isinstance(err, TypeError):
                        return JsonResponse({
                            'status': 415,
                            'message': "Error",
                            'err': "The password/encryption key you provided is incorrect"
                        })
        elif job.status() == 'error':
            return JsonResponse({
                'status' : 415,
                'message' : "Error",
                'errs' : job.errs
            })
        else:
            params['job_info'] = "Your task has not been completed yet. Once it is successfully processed on our server, we will promptly update the page with the completed results."
            return JsonResponse({
                'status': 102,
                'message': params['job_info']
            })

# ------------------------ Info View ------------------------ #
@update_user_last_active
def get_job_info(req,job_type,job_id):
    if job_type not in ["encryption","steganos","picit"]:
        return JsonResponse({
            'status' : 404,
            'message' : "No such type of job exists"
        })
    uinfo = req.session.get('userinfo')
    params = {}
    if uinfo:
        params = {
            'userinfo' : uinfo.copy()
        }

    try:
        job = ImageJob.objects.get(id=job_id,name=job_type)
    except ImageJob.DoesNotExist:  # 400
        return JsonResponse({
            'status': 400,
            'message': "Requested job does not exist."
        })
    else:
        if uinfo:
            user = User.objects.get(id=uinfo['id'])
            if job.user_id != user.id:  # 403
                return JsonResponse({
                    'status': 403,
                    'message': "You do not have permission to access this file."
                })
            if job.status() == "Finished":
                return JsonResponse({
                    'status' : 200,
                    'message' : job.status(),
                    'job_info' : job.dict()
                })
            elif job.status() == "error":
                return JsonResponse({
                    'status' : 415,
                    'message': "Error",
                    'errs' : job.errs
                })
            else:
                return JsonResponse({
                    'status': 102,
                    'message': "Your task has not been completed yet. Once it is successfully processed on our server, we will promptly update the page with the completed results.",
                    'job_info' : job.dict()
                })
        else:
            session_key = req.session.session_key
            if job.user_id != session_key:
                return JsonResponse({
                    'status': 403,
                    'message': "You do not have permission to access this file."
                })
            if job.status() == "Finished":
                return JsonResponse({
                    'status' : 200,
                    'message' : job.status(),
                    'job_info' : job.dict()
                })
            elif job.status() == "error":
                return JsonResponse({
                    'status' : 415,
                    'message': "Error",
                    'errs' : job.errs
                })
            else:
                return JsonResponse({
                    'status': 102,
                    'message': "Your task has not been completed yet. Once it is successfully processed on our server, we will promptly update the page with the completed results.",
                    'job_info' : job.dict()
                })
