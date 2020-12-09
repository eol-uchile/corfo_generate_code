/*
        .-"-.
       /|6 6|\
      {/(_0_)\}
       _/ ^ \_
      (/ /^\ \)-'
       ""' '""
*/


function CorfoGenerateXBlock(runtime, element, settings) {
    var $ = window.jQuery;
    var $element = $(element);
    
    $(element).find('input[name=corfo-get-code]').live('click', function(e) {
        /* 
            .
        */
        e.currentTarget.disabled = true;
        $.ajax({
            type: "GET",
            url: settings.url_get_code,
            data: {
                'course_id': settings.course_id,
                'id_content': settings.id_content,
                'content': settings.content
            },
            success: function(response) {
                if(response.result == 'success'){

                }
                else{
                    $element.find('.corfogeneratecode_error')[0].textContent = response.message;
                }
            },
            error: function() {
                alert("Error inesperado ha ocurrido. Actualice la página e intente nuevamente")
            }
        });
    });
}
