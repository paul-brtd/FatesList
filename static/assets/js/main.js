function submit_bot(){
    var form=$("#bot_form")
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

$("#bot_form").submit( function(eventObj) {
    var input = $("<input>").attr({"type":"hidden","name":"tags"}).val(instance.value());
    $('#bot_form').append(input);
    return true;
});
