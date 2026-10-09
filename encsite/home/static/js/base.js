function object_to_URI_string(obj){
    let rstr = "";
    Object.keys(obj).forEach(function(key){
        rstr += `${encodeURIComponent(key)}=${encodeURIComponent(obj[key])}&`
    });
    return rstr.slice(0,rstr.length-1); 
}

function capitalize_first(str) {
    let capped = "";
    for(let i=0;i<str.length;i++){
        if(i===0){
            capped += str[i].toUpperCase();
        }
        else{
            capped += str[i];
        }
    }
    return capped;
}

function get_file(file_input){
    [ifile] = file_input.files;
    return ifile;
}

function get_file_type(file){
    return file.type || 'unknown';
}

function show_hide(e){
    if(this.value===''){
        return;
    }
    if (this.type=='text'){
        this.type = 'password';
    }
    else{
        this.type = 'text';
    }
}

function download_text_file(data,filename) {
    try {
        let ts = ((Date.now())/1000).toString().split('.')[0];
        filename = filename.replace("$ts",ts)
    } catch (error) {
        console.log("");
    }
    const txtfile_blob = new Blob([data], { type: 'text/plain' });
    const txtfile_dbtn = window.document.createElement('a');
    txtfile_dbtn.href = window.URL.createObjectURL(txtfile_blob);
    txtfile_dbtn.target = '_blank';
    txtfile_dbtn.download = filename;
    txtfile_dbtn.click();
}

function get_csrf_token(){
    let [csrf_input] = document.getElementsByName("csrfmiddlewaretoken");
    return csrf_input.value;
}

function preventDefault(e){
    e.preventDefault();
}

function enableDropFiles(element,fileInput){
    element.ondragover = preventDefault;
    element.ondragenter = preventDefault;
    element.ondrop = function(e){
        fileInput.files = e.dataTransfer.files;
        fileInput.onchange();
        e.preventDefault();
    }
}

function getDateTimeStr(dt){
    let months = [
        "January",
        "February", 
        "March", 
        "April", 
        "May", 
        "June", 
        "July", 
        "August", 
        "September", 
        "October", 
        "November", 
        "December"
    ];
    let seconds = dt.getSeconds();
    let minutes = dt.getMinutes();
    let hours = dt.getHours();
    let day = dt.getDate();
    let month = dt.getMonth();
    let year = dt.getFullYear();
    let ampm = "AM";
    if (hours > 12) {
        hours -= 12;
        ampm = "PM";
    }
    let tcomponents = [day,hours,minutes,seconds];
    for(let i = 0;i<tcomponents.length;i++){
        if(tcomponents[i]<10){
            tcomponents[i] = `0${tcomponents[i]}`;
        }
    }
    [day,hours,minutes,seconds] = tcomponents;
    let tz_full_name = String(String(dt).split("(")[1]).split(")")[0];
    return `${day}/${months[month]}/${year} - ${hours}:${minutes}:${seconds} ${ampm} [${tz_full_name}]`;
}