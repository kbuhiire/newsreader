/*-------------------------------------------------------------------------

	Theme Name: EGO - html - v.1
	
	For any questions concerning this theme please refer to documention or
	our forum at support.udfrance.com.

/*------------------------------------------------------------------------

//GENERAL FUNCTONS ///////////////////////////////////////////////////////

-------------------------------------------------------------------------*/

$(document).ready(function() {


	/*vars used throughout*/
	var thumb = $('.thumb,.round-thumb'),
		thumbW,
		thumbH,
		thumbCaption,
		target,
		hoverSpeed = 500,
		hoverEase = 'easeOutExpo',
		targetNetwork = $('ul.socialSmall li a'),
		toggleMenu = $('.mobileMenuToggle'),
		lightboxTransition = 'fade', //Set lightbox transition type
		overlayOpacity = 0.8, //Fancybox overlay opacity
		overlayColor = '#000', //Fancybox overlay color	
		videoWidth = 663, //Fancybox video width
		videoHeight = 372; //Fancybox video height
	lazyload = true;



	//LAZY LOADING -------------------------------------------------------------------------/


	$(function() {

		if (lazyload === false || isMobile === true) return false;

		$("img.lazy").lazyload({
			placeholder: "",
			effect: "fadeIn"
		});

	});


	//MOBILE MENU -----------------------------------------------------------------------/


	toggleMenu.on('click', function(event) {

		if ($(this).parent().find('ul.navigation').is(':hidden')) {

			$(this).parent().find('ul.navigation').slideDown();
			$(this).addClass('open');


		} else {

			$(this).parent().find('ul.navigation').slideUp();
			$(this).removeClass('open');


		}

		event.preventDefault();

	});


	//ROLLOVER SPECIFIC ---------------------------------------------------------------------/


	/*general
	-------------------*/

	thumb.on({

		mouseenter: function() {

			//check if device is mobile 
			//or within an inactive filter category
			//or if its video content in which case do nothing
			if (isMobile === true) return false;

			thumbW = thumb.find('a').find('img').width();
			thumbH = thumb.find('a').find('img').height();

			//get refrences needed
			thumbCaption = $(this).find('a').attr('title');

			//add rolloverscreen
			if (!$(this).find('a').find('div').hasClass('thumb-rollover')) $(this).find('a').append('<div class="thumb-rollover"></div>');


			//set it to the image size and fade in
			hoverScreen = $('.thumb-rollover');
			hoverScreen.css({
				width: thumbW,
				height: thumbH
			});


			//make sure caption is filled out
			if (typeof thumbCaption !== 'undefined' && thumbCaption !== false && $(this).find(hoverScreen).is(':empty')) {

				//construct rollover & animate
				$(this).find(hoverScreen).append('<div class="thumbInfo">' + thumbCaption + '</div>');
				target = $(this).find(hoverScreen);
				target.stop().animate({
					opacity: 1
				}, hoverSpeed, hoverEase);
			}

		},

		mouseleave: function() {

			if (isMobile === true) return false;

			//animate out
			$(this).find(hoverScreen).animate({
				opacity: 0
			}, hoverSpeed, hoverEase, function() {

				//delete rollover
				$(this).remove();

			});


		}

	});
});