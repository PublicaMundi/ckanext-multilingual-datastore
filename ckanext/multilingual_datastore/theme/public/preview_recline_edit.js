// recline preview module
var dataExplorer;
//var LANGUAGE =  'fr';
var errorMsg;
var views;
var grid;
this.ckan.module('recline_translate_edit_preview', function (jQuery, _) {  
  return {
    options: {
      i18n: {
        heading: _("Please Confirm Action"),
        datastore_disabled: _("Datastore is disabled. Please enable datastore and try again in order to proceed with resourcer translationm"),
        confirm_delete: _("Are you sure you want to delete column translation?"),
        confirm_update: _("Are you sure you want to update existing column translation?"),
        confirm_publish: _("Are you sure you want to publish resource translation?"),
        same_as_original: _("Cannot translate in original language."),
        errorLoadingPreview: _("Could not load preview"),
        errorDataProxy: _("DataProxy returned an error"),
        errorDataStore: _("DataStore returned an error"),
        previewNotAvailableForDataType: _("Preview not available for data type: ")
      },
    template: [
        '<div class="modal">',
        '<div class="modal-header">',
        '<a href="#" class="close" data-dismiss="modal">&times;</a>',
        '<h3>Tranlate Column Title</h3>',
        '</div>',
        '<div class="modal-body">',
        '<div class="divDialogElements">',
        '<label style="display:inline-block"><h4>Title:</h4></label>',
        '<label style="display:inline-block" id="labelTitleOriginal"><h4></h4></label>',
        '<br>',
        '<label for="inputTitleTrans"><h4>Translation:</h4></label>',
        '<input class="medium inputTitleTrans" id="inputTitleTrans" name="xlInput" type="text" />',
        '</div>',
        '</div>',
        '<div class="modal-footer">',
        '<a href="#" class="btn btn-cancel" id="closeDialog">Cancel</a>',
        '<a href="#" class="btn btn-primary" id="okClicked">OK</a>',
        '</div>',
        '</div>'
      ].join('\n'),

      site_url: ""
    },

    initialize: function () {
      jQuery.proxyAll(this, /_on/);
      // hack to make leaflet use a particular location to look for images
      //this.button = jQuery("#button");
      //var html = '<a href="#" class="btn" id="saveClicked">Save</a> <a href="#" class="btn btn-primary" id="publishClicked">Publish</a>';
      this.save_btn = jQuery("#saveClicked");
      this.publish_btn = jQuery("#publishClicked");
      this.el.ready(this._onReady);
    },
    _onReady: function() {
      this.loadPreviewDialog(preload_resource);  
    },

    // **Public: Loads a data preview**
    //
    // Fetches the preview data object from the link provided and loads the
    // parsed data from the webstore displaying it in the most appropriate
    // manner.
    //
    // link - Preview button.
    //
    // Returns nothing.
    loadPreviewDialog: function (resourceData) {
      var self = this;

      function showError(msg){
        msg = msg || _('error loading preview');
        window.parent.ckan.pubsub.publish('data-viewer-error', msg);
      }

      recline.Backend.DataProxy.timeout = 10000;

      // 2 situations
      // a) something was posted to the datastore - need to check for this
      // b) csv or xls (but not datastore)
      resourceData.formatNormalized = this._normalizeFormat(resourceData.format);

      resourceData.url  = this._normalizeUrl(resourceData.url);
      if (resourceData.formatNormalized === '') {
        var tmp = resourceData.url.split('/');
        tmp = tmp[tmp.length - 1];
        tmp = tmp.split('?'); // query strings
        tmp = tmp[0];
        var ext = tmp.split('.');
        if (ext.length > 1) {
          resourceData.formatNormalized = ext[ext.length-1];
        }
      }
      var lang = this.options.translation_language;
      
      // Datastore
      if (resourceData.datastore_active) {
        if (!("translation_resource" in resourceData)){
            resourceData.backend =  'ckanTranslateEdit';
        }
        else{
            resourceData.backend =  'ckan';
        }
        // Set endpoint of the resource to the datastore api (so it can locate
        // CKAN DataStore)
        //resourceData.endpoint = jQuery('body').data('site-root') + 'api';
        resourceData.endpoint = this.options.site_url + 'api';
        resourceData.translation_language = lang;
         
        var dataset = new recline.Model.Dataset(resourceData);
         
        errorMsg = this.options.i18n.errorLoadingPreview + ': ' + this.options.i18n.errorDataStore;
        
        translate = new TranslateHelper(resourceData, lang); 
        var res_trans_id; 
        try{
            res_trans_id = JSON.parse(resourceData.has_translations)[lang];
            this.options.res_trans_id = res_trans_id;
        }
        catch(err) {
            
        }

        var orig_lang = resourceData.resource_language || 'el';

        if (orig_lang == lang){
          alert(self.i18n('same_as_original'));
            // TODO: DOesnt work
          self.sandbox.notify(self.i18n('same_as_original'), 'error');
        }
        else if (res_trans_id === undefined  && !("translation_resource" in resourceData)){
            
            //console.log("NEW TRANSLATION");
            var transResource = translate.create(function() {}, function() { 
            var translations = {};
                try{
                     translations = JSON.parse(resourceData.has_translations)
                }
                catch(err){
            
                }
            translations[lang] = transResource.responseJSON.result.id;
            resourceData.has_translations = JSON.stringify(translations);
            
            dataset = new recline.Model.Dataset(resourceData);
                    
            self.initializeDataset(dataset, resourceData);
            });
        }
        else{
            //console.log("PREVIOUS TRANSLATION");
            var translationResource = null;
            this.initializeDataset(dataset, resourceData);
        }
      }
      else{
          //TODO: doesnt work for some reason
          self.sandbox.notify(self.i18n('datastore_disabled'), 'error');
      }
    },
    _onComplete: function(){
        dataExplorer.model.fetch();
        //.done(function(dataset){
        //});
    },
    _onLoad: function(){
        dataExplorer.notify({message: 'Loading', loader:true, category: 'warning', persist: true});
        //setTimeout(function(){ dataExplorer.model.fetch()}, 3000);
    },

    initializeDataset: function(dataset, resourceData) {
        var self = this;
        
        
     function showError(msg){
        msg = msg || _('error loading preview');
        window.parent.ckan.pubsub.publish('data-viewer-error', msg);
      }

                self._onInitializeDataExplorer(dataset);
                

                //self._onComplete();   

                dataset.bind('translate-no', function(col){
                    var options = {column:col.id};
                    self.deleteWithConfirmation(dataset, options); 
                });
                            
                dataset.bind('translate-manual', function(col){
                    var options = {column:col.id, mode:'manual'};
                    self.updateWithConfirmation(dataset, options); 
                });

                dataset.bind('transcript', function(col){
                    var options = {column:col.id, mode:'transcription'};
                    self.updateWithConfirmation(dataset, options); 
                });

                dataset.bind('translate-auto', function(col){
                    //TODO
                    var options = {column:col.id, mode:'automatic'};
                    self.updateWithConfirmation(dataset, options); 
                });
    
                dataset.bind('translate-title', function(col){
                    dataset.save();
                    var options = {column:col.id, translation: col.translation, mode:'title'};
                    self.updateWithConfirmation(dataset, options); 
                });

                dataset.queryState.bind('save', function(){

                    dataset.save();
                    
                });

                self.save_btn.click(function() {
                    dataset.save();
                    dataExplorer.notify({message: 'Loading', loader:true, category: 'warning', persist: false});
                });
                self.publish_btn.click(function() {
                        //TODO: Save before publishing, need timeout?
                        dataset.save();
                        self.publishWithConfirmation(self._onLoad, function() { 
                            window.top.location.href = '/dataset/' + resourceData.package_name;
                        }); 

                })
                
          //      });
        //
        //  })
        //  .fail(function(error){
        //    if (error.message) errorMsg += ' (' + error.message + ')';
        //    showError(errorMsg);
        //  });
    },
    _onSuccess: function(e) {
    },
    getTransSuffix: function(lang){
        return '-' + lang;
    },
    removeTransSuffix: function(title, lang){
        return title.substring(0, title.indexOf("-"+lang));
    },
    _onInitializeDataExplorer: function (dataset) {
      views = [
        {
          id: 'grid',
          label: 'Grid',
          view: new recline.View.SlickGrid({
            model: dataset,
            state: { gridOptions: {editable: true} }
            //state: { gridOptions: {editable:true, editorFactory: {getEditor:this._onEditor} } }
          })
        },
        
        ];

      var sidebarViews = [
        {
          id: 'valueFilter',
          label: 'Filters',
          view: new recline.View.ValueFilter({
            model: dataset
          })
        }
      ];

      dataExplorer = new recline.View.MultiView({
        el: this.el,
        model: dataset,
        views: views,
        sidebarViews: sidebarViews,
        config: {
          readOnly: true,
        }
      });
    },

    _normalizeFormat: function (format) {
      var out = format.toLowerCase();
      out = out.split('/');
      out = out[out.length-1];
      return out;
    },
    _normalizeUrl: function (url) {
      if (url.indexOf('https') === 0) {
        return 'http' + url.slice(5);
      } else {
        return url;
      }
    },
    deleteWithConfirmation: function(dataset, options, ld, cb) {
        //var res = {id:this.options.res_trans_id, endpoint:this.options.resourceData.endpoint};
            var ld = ld || this._onLoad;
            var cb = cb || this._onComplete;
            var field_exists = this.checkFieldExists(dataset, options);

            if (field_exists){
                var col_translation = '';
                this.options.helper = translate;
                this.options.action = 'delete';
                this.options.options = options;
                this.options.cb = cb;
                this.options.ld = ld;
                
                this.confirm(this.i18n('confirm_delete'));

            }
            else{
                translate.delete(options, this._onLoad, this._onComplete);
            }        
    },
    publishWithConfirmation: function(ld, cb) {
        var ld = ld || this._onLoad;
        var cb = cb || this._onComplete;
        this.options.helper = translate;
        this.options.action = 'publish';
        this.options.options = {};
        this.options.cb = cb;
        this.options.ld = ld;
        this.confirm(this.i18n('confirm_publish'));
    },
    updateWithConfirmation: function(dataset, options, ld, cb) {
            
            var ld = ld || this._onLoad;
            var cb = cb || this._onComplete;
            var field_exists = this.checkFieldExists(dataset, options);
            options.selectable = false;
            
            if (options.mode == 'title'){
                    this.options.helper = translate;
                    this.options.action = 'update';
                    this.options.options = options;
                    this.options.ld = ld;
                    this.options.cb = cb;

                    this.confirmTitle(options.column);
                   if (options.translation){
                        $('.inputTitleTrans').val(options.translation);
                   }
                   else{
                        $('.inputTitleTrans').val('');
                   }

                    $('.inputTitleTrans').on('input', function(e){
                        options.title_trans = e.target.value;
                    });

            } 
            else{ 
                if (field_exists){
                    var col_translation = '';
                    this.options.helper = translate;
                    this.options.action = 'update';
                    this.options.options = options;
                    this.options.ld = ld;
                    this.options.cb = cb;
                
                    this.confirm(this.i18n('confirm_update'));
                }
                else{
                    translate.update(options, this._onLoad, this._onComplete);
                } 
            }       
    },
    checkFieldExists: function(dataset, options){
        var lang = this.options.translation_language;
        var col = options.column+this.getTransSuffix(lang);
        var fields = dataset.fields.models;
        var field_exists = false; 
        fields.forEach(function(fld, idx){
            if (fld.id == col){
                field_exists = true;
                return;
            }
        });
        return field_exists;
    },

    confirm: function (text) {
      this.sandbox.body.append(this.createModal(text));
      this.modal.modal('show');
      
       // Center the modal in the middle of the screen.
      this.modal.css({
        'margin-top': this.modal.height() * -0.5,
        'top': '50%'
      });
    },
    confirmTitle: function(text) {
        this.sandbox.body.append(this.createModalFromTemplate(text));
        this.modal.modal('show');
       // Center the modal in the middle of the screen.
      this.modal.css({
        'margin-top': this.modal.height() * -0.5,
        'top': '50%'
      });
    },
     createModalFromTemplate: function(col_name) {
        var element = this.modal = jQuery(this.options.template);
        element.on('click', '.btn-primary', this._onConfirmSuccess);
        element.on('click', '.btn-cancel', this._onConfirmCancel);
        element.modal({show: false});
        //element.find('h3').text(this.i18n('heading'));
        element.find('#labelTitleOriginal h4').text(col_name);
      
      return this.modal;
    },
     createModal: function (text) {
      //if (!this.modal) {
      // re-create modal everytime it is called
        var element = this.modal = jQuery(this.options.template);
        element.on('click', '.btn-primary', this._onConfirmSuccess);
        element.on('click', '.btn-cancel', this._onConfirmCancel);
        element.modal({show: false});
        element.find('h3').text(this.i18n('heading'));
        element.find('.modal-body').text(text);
        
        element.find('.btn-primary').text(this.i18n('confirm'));
        element.find('.btn-cancel').text(this.i18n('cancel'));
      //}
      return this.modal;
    },

    /* Event handler for the success event */
    _onConfirmSuccess: function (e) {
        var h = this.options.helper;
        var action = this.options.action;
        var options = this.options.options;
        var ld = this.options.ld;
        var cb = this.options.cb;
        this.sandbox.body.append(h[action](options, ld, cb));
      this.modal.modal('hide');
    },

    /* Event handler for the cancel event */
    _onConfirmCancel: function (event) {
      this.modal.modal('hide');
    }

  };
});




