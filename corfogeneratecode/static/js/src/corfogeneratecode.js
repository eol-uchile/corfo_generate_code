/*
        .-"-.
       /|6 6|\
      {/(_0_)\}
       _/ ^ \_
      (/ /^\ \)-'
       ""' '""
*/


function CorfoGenerateXBlock(runtime, element) {
    var $ = window.jQuery;
    var $element = $(element);
    var handlerUrl = runtime.handlerUrl(element, 'generate_code');
    var handlerUrl_rut = runtime.handlerUrl(element, 'generate_code_rut');
    $(element).find('#corfo-get-code').live('click', function(e) {
        /* 
            Get corfo code from api
        */
        $(element).find('#ui-loading-corfogeneratecode-load').show()
        e.currentTarget.disabled = true;
        $.post(handlerUrl, JSON.stringify({})).done(function(response) {
           if(response.result == 'success'){
                $element.find('#corfo_code')[0].textContent = response.code;
                $element.find('#corfo_user_rut')[0].textContent = response.user_rut;
                $(element).find('#corfo-get-code').hide()
                $(element).find('#label_corfo_code').show();
                $element.find('.corfogeneratecode_error')[0].innerHTML = '';
            }
            else{
                $(element).find('#corfo-get-code').hide()
                $element.find('.corfogeneratecode_error')[0].innerHTML = response.message;
            }
            $(element).find('#ui-loading-corfogeneratecode-load').hide()
        }).fail(function() {
            $(element).find('#ui-loading-corfogeneratecode-load').hide()
            alert("Error inesperado ha ocurrido. Actualice la página e intente nuevamente.")
        });
    });
    $(element).find('#corfo-get-code-rut').live('click', function(e) {
        /* 
            Get corfo code from api
        */
        $(element).find('#ui-loading-corfogeneratecode-load').show()
        e.currentTarget.disabled = true;
        let user_rut = $(element).find('#corfo_rut').val();
        $.post(handlerUrl_rut, JSON.stringify({'user_rut': user_rut})).done(function(response) {
           if(response.result == 'success'){
                $element.find('#corfo_code')[0].textContent = response.code;
                $element.find('#corfo_user_rut')[0].textContent = response.user_rut;
                $(element).find('#corfo-get-code-rut').hide()
                $(element).find('#corfo_rut_div').hide()
                $(element).find('#label_corfo_code').show();
                $(element).find('#label_corfo_user_rut').show();
                $element.find('.corfogeneratecode_error')[0].innerHTML = '';
            }
            else{
                if(response.status == 8 || response.status == 9 || response.status == 10) {
                    e.currentTarget.disabled = false;
                    $(element).find('#corfo-get-code-rut').show();
                }
                else $(element).find('#corfo-get-code-rut').hide();
                $element.find('.corfogeneratecode_error')[0].innerHTML = response.message;
            }
            $(element).find('#ui-loading-corfogeneratecode-load').hide()
        }).fail(function() {
            $(element).find('#ui-loading-corfogeneratecode-load').hide()
            alert("Error inesperado ha ocurrido. Actualice la página e intente nuevamente.")
        });
    });
}
