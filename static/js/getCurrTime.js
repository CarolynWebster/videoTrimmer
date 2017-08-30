function getCurrentTime() {
    // create a new date object
    var d = new Date();
    var month = d.getMonth() + 1;
    var date = d.getDate();
    var year = d.getFullYear();
    var hour = d.getHours();
    var min = d.getMinutes();

    if (hour > 12) {
        hour = hour - 12;
    }

    return String(month + "_" + date + "_" + year + "_" + hour + "-" + min)
}
