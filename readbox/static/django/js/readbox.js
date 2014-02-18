// login
$(document).ready(function() {

    $("#loginButtonHeader").on("click", function () { $("#modalTab").first().trigger("click"); });

    $('#loginForm').submit(function(e){
        $('#loginButton').attr("disabled", true);
        $('#spinnerLogin').show();
        e.preventDefault();
        var form = $(e.target);

        $.ajax({
            url: '/login/',
            type: 'post',
            data: form.serialize(),
            error: function(){
                $('#spinnerLogin').hide();
                $('#loginMessage').addClass('alert alert-error').html('<b>Oh Snap!</b> Wrong email or password.');
                $('#loginButton').attr("disabled", false).html('Log In');
            },
            success: function(){
                $('#loginButton').attr("disabled", true);
                window.location.replace("/reader/");
            }
        });
     });

    $('#registrationForm').submit(function(e){
        e.preventDefault();
        $('#spinnerSignup').show();
        $('#registrationButton').attr("disabled", true);
        var form = $(e.target);

        $.ajax({
            url: '/registration/',
            type: 'post',
            data: form.serialize(),
            error: function(xhr){
                $('#spinnerSignup').hide();
                $('#registrationMessage').addClass('alert alert-danger').html('<b>Oh Snap!</b> ' + xhr.responseText);
                $('#registrationButton').attr("disabled", false);
            },
            success: function(){
                $('#spinnerSignup').hide();
                $('#registrationMessage').removeClass('alert-danger').addClass('alert alert-success').html('<b>Yay!</b> We sent you a verification email.');
                $('#registrationDone').hide();
                $('#registrationButton').attr("disabled", true);
            }
        });
     });
});