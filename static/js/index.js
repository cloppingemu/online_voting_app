var i = 1;
considered = [];

function addVote(key, name, numCan){
    if ((i <= numCan) && !(considered.includes(key))) {
        document.getElementById("rank"+i).innerHTML = name;
        considered.push(key);
        i++;
        document.getElementById("ballot").value = String(considered);
    }
    else{
        document.getElementById("alert_area2").innerHTML = ("!! " + "Overflow or repeat attempted");
    }
}

function removeVote(){
    if (i > 1){
        document.getElementById("rank"+(i-1)).innerHTML = "";
        considered.pop()
        i--;
        document.getElementById("ballot").value = String(considered)
    }
    else{
        document.getElementById("alert_area2").innerHTML = ("!! " + "Underflow attempted");
    }
}

function removeAllVotes(numCan){
    i=1;
    while (i <= numCan){
        document.getElementById("rank"+i).innerHTML = "";
        i++;
    }
    i = 1;
    considered = [];
    document.getElementById("ballot").value = String(considered)
}

function validate(fieldId, validationAlert){
    if(document.getElementById(fieldId).value == ""){
        document.getElementById("alert_area1").innerHTML = "!! " + validationAlert;
        document.getElementById(fieldId).focus();
        return false;
    }
    else{
        return true;
    }
}

function validateVotes(message, minNum){
    if (considered.length < minNum){
        document.getElementById("alert_area1").innerHTML = "!! " + message;
        return false;
    }
    else{
        return true;
    }
}

