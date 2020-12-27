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