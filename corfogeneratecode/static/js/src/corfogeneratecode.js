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
    
    $(element).find('#corfo-get-code').live('click', function(e) {
        /* 
            Get corfo code from api
        */
        $(element).find('#ui-loading-corfogeneratecode-load').show()
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
                    $element.find('#corfo_code')[0].textContent = response.code;
                    $(element).find('#corfo-get-code').hide()
                    $(element).find('#label_corfo_code').show();
                    $element.find('.corfogeneratecode_error')[0].textContent = '';
                }
                else{
                    $(element).find('#corfo-get-code').hide()
                    $element.find('.corfogeneratecode_error')[0].textContent = response.message;
                }
                $(element).find('#ui-loading-corfogeneratecode-load').hide()
            },
            error: function() {
                $(element).find('#ui-loading-corfogeneratecode-load').hide()
                alert("Error inesperado ha ocurrido. Actualice la página e intente nuevamente.")
            }
        });
    });
}
