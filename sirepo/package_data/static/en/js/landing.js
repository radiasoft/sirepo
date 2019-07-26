$(function() {
  if ($('body').hasClass('landing')) {
    // Slider
    if ($('.get-started').length > 0) {
      var steps = 4;
      var current_step = 1;

      // Calculate where the steps should be
      var step_transition = function() {
        $('.get-started-step-images').css('transform', 'translateX(' + (100 * current_step - 100) / -4 + '%)');

        $('.get-started-step-icon, .get-started-step').removeClass('active');
        $('.get-started-step-icon[data-step="' + current_step + '"], .get-started-step[data-step="' + current_step + '"]').addClass('active');

        $('.get-started-next, .get-started-prev').removeClass('hidden');

        if (current_step === steps) {
          $('.get-started-next').addClass('hidden');
        }

        if (current_step === 1) {
          $('.get-started-prev').addClass('hidden');
        }
      }

      // Next click
      $('.get-started-next').on('click', function() {
        if (current_step < steps) {
          current_step++;
          step_transition();
        }
      });

      // Prev click
      $('.get-started-prev').on('click', function() {
        if (current_step > 1) {
          current_step--;
          step_transition();
        }
      });

      // Icon click
      $('.get-started-step-icon').on('click', function() {
        current_step = $(this).attr('data-step')
        step_transition();
      })

      // Left or right arrows
      $(document).on('keyup', function(e) {
        switch(e.which) {
          case 37: // left
            e.preventDefault();
            if (current_step > 1) {
              current_step--;
              step_transition();
            }
            break;

          case 39: // right
            e.preventDefault();
            if (current_step < steps) {
              current_step++;
              step_transition();
            }
            break;
        }
      });

      // Initial Step
      step_transition(current_step);

      // Size step copy since they're position absolute
      var resize_steps = function() {
        var max_height = 0;
        $('.get-started-step').each(function(i, step) {
          if ($(step).outerHeight() > max_height) {
            max_height = $(step).outerHeight();
          }

          $('.get-started-steps').height(max_height);
        })
      }

      // Simple resizing of step copy on window resize with throttle
      var step_resize_timeout = null;
      $(window).on('resize', function() {
        clearTimeout(step_resize_timeout);
        step_resize_timeout = setTimeout(resize_steps, 100);
      });

      resize_steps();
    }

    // Populate news if it's on the page
    if ($('.news-announcements').length > 0) {
      // Use jQuery to load files here since it's already installed

      // Fetch article index
      $.get(
        '/en/news/article-index.json',
        function(articles) {
          var converter = new showdown.Converter();
          var articles_html = [];
          var promises = [];

          var now = new Date();
          now.setHours(0);
          now.setMinutes(0);
          now.setSeconds(0);

          // Fetch each article
          $.each(articles, function(index, article) {
            var start_date, end_date;

            if (article.start_date) {
              var start_date_parts = article.start_date.split('/');
              start_date  = new Date(start_date_parts[0], parseInt(start_date_parts[1]) - 1, start_date_parts[2]);
            } else {
              start_date = now;
            }

            if (article.end_date) {
              var end_date_parts = article.end_date.split('/');
              end_date    = new Date(end_date_parts[0], parseInt(end_date_parts[1]) - 1, end_date_parts[2]);
            } else {
              end_date = now;
            }

            if (now >= start_date && now <= end_date) {
              promises.push(
                $.get(
                  '/en/news/' + article.markdown_file,
                  function(article_md) {
                    articles_html[index] = converter.makeHtml(article_md);
                  }
                )
              );
            }
          });

          if (promises.length > 0) {
            $('.news-announcements').removeClass('hidden');

            $.when.apply(this, promises).then(function() {
              $.each(articles_html, function(index, article_html) {
                if (article_html) {
                  $('.news-announcements-items').append('<article>' + article_html + '</article>');
                }
              })
            });
          }
        }

      );
    }
  }
});
