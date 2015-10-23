this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};
this.recline.Backend.Ckan = this.recline.Backend.Ckan || {};

(function ($) {
  function TranslateColumnPicker(model, columns, grid, options) {
    var $menu;
    var columnCheckboxes;
    var column;
    var lang;
    var defaults = {
      fadeSpeed:250
    };

    function getTransSuffix(lang){
        return '-' + lang;
        };

    function init() {
        // hack to get language from url
        lang = window.location.pathname.slice(-2);
     
      grid.onHeaderContextMenu.subscribe(handleHeaderContextMenu);
      options = $.extend({}, defaults, options);
      $menu = $('<ul class="dropdown-menu slick-contextmenu" style="display:none;position:absolute;z-index:20;" />').appendTo(document.body);
      $menu.bind('mouseleave', function (e) {
        $(this).fadeOut(options.fadeSpeed);
      });
      $menu.bind('click', updateColumn);

    }

    function handleHeaderContextMenu(e, args) {
      e.preventDefault();
     
      
      $menu.empty();
      columnCheckboxes = [];

      var $li, $input, $label;
      
      if (args.column.id.indexOf(getTransSuffix(lang))>0){
         return;
         
      
      }
      else{
      
      $li = $('<li />').appendTo($menu);
      $label = $('<label />')
        .text('Automatic Translation')
        .appendTo($li);

      $input = $('<input type="checkbox" />').data('option', 'translate-automatic').attr('id','translate-automatic');
      $input.appendTo($label);
      columnCheckboxes.push($input);

      $li = $('<li />').appendTo($menu);
      $label = $('<label />')
          .text('Manual Translation')
          .appendTo($li);

      $input = $('<input type="checkbox" />').data('option', 'translate-manual').attr('id','translate-manual');
      $input.appendTo($label);
      columnCheckboxes.push($input);
      
      $li = $('<li />').appendTo($menu);
      $label = $('<label />')
          .text('Transcription')
          .appendTo($li);

      $input = $('<input type="checkbox">').data('option', 'transcript').attr('id','transcript');
      $input.appendTo($label);
      columnCheckboxes.push($input);

      $li = $('<li />').appendTo($menu);
      $label = $('<label />')
          .text('Non Translatable')
          .appendTo($li);

      $input = $('<input type="checkbox">').data('option', 'translate-no').attr('id','translate-no');
      columnCheckboxes.push($input);
      $input.appendTo($label);
      
      $('<hr>').appendTo($menu);
      $li = $('<li />').appendTo($menu);
        $label = $('<label />')
            .text('Translate Title')
            .appendTo($li);

        $input = $('<input type="checkbox" />').data('option', 'translate-title').attr('id','translate-title');
        $input.appendTo($label);
        columnCheckboxes.push($input);

      }
      
      $menu.css('top', e.pageY - 10)
          .css('left', e.pageX - 10)
          .fadeIn(options.fadeSpeed);
        column = args.column;
    }

    function updateColumn(e) {
        console.log('updatiiiing');
        console.log(column.state);
      var checkbox;
      if ($(e.target).data('option') === 'translate-no' ){
          model.trigger('translate-no', column);

      }
        else if ($(e.target).data('option') === 'title'){
        model.trigger('title', column);
        }    
        else if ($(e.target).data('option') === 'transcript'){
        model.trigger('transcript', column);
        
      }

      else if ($(e.target).data('option') === 'translate-manual'){
        model.trigger('translate-manual', column);
        
      }
      else if ($(e.target).data('option') === 'translate-automatic'){
        model.trigger('translate-auto', column);

      }
      else if ($(e.target).data('option') === 'translate-title'){
        model.trigger('translate-title', column);

      }

      if ($(e.target).data('option') === 'autoresize') {
        var checked;
        if ($(e.target).is('li')){
            checkbox = $(e.target).find('input').first();
            checked = !checkbox.is(':checked');
            checkbox.attr('checked',checked);
        } else {
          checked = e.target.checked;
        }

        if (checked) {
          grid.setOptions({forceFitColumns:true});
          grid.autosizeColumns();
        } else {
          grid.setOptions({forceFitColumns:false});
        }
        options.state.set({fitColumns:checked});
        return;
      }
    }
    init();
  }
  // Slick.Controls.ColumnPicker
    $.extend(true, window, { Slick:{ Controls:{ TColumnPicker:TranslateColumnPicker }}});
})(jQuery);




