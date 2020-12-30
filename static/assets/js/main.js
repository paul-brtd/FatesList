$('[tool-tip-toggle="tooltip-demo"]').tooltip({
 
    placement : 'top'

});


var input = document.getElementById("search_input");

// Execute a function when the user releases a key on the keyboard
input.addEventListener("keyup", function(event) {
// Number 13 is the "Enter" key on the keyboard
if (event.keyCode === 13) {
// Cancel the default action, if needed
event.preventDefault();
// Trigger the button element with a click
document.getElementById("search").click();
}
});

$("#search").click(function(){
query = $("#search_input").val()
document.location.href = "/search/" + encodeURIComponent(query)
})

function submit_bot(){

    var unindexed_array = $("#bot_form").serializeArray();
    var indexed_array = {};

    $.map(unindexed_array, function(n, i){
        indexed_array[n['name']] = n['value'];
    });
    $.ajax({
        type: 'POST',
        dataType: 'json',
        url: '/bot/add',
        data: JSON.stringify({"form":indexed_array,"tags":instance.value()}),
        success: function(responseData, textStatus) {
            // you implementation logic here
        },
        complete: function(textStatus) {

        },
        error: function(responseData)
        {

        }
    });
}