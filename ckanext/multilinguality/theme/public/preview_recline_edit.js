// recline preview module
var dataExplorer;
//var LANGUAGE =  'fr';
var errorMsg;

this.ckan.module('reclinepreview', function (jQuery, _) {  
  return {
    options: {
      i18n: {
        errorLoadingPreview: "Could not load preview",
        errorDataProxy: "DataProxy returned an error",
        errorDataStore: "DataStore returned an error",
        previewNotAvailableForDataType: "Preview not available for data type: "
      },
      site_url: ""
    },

    initialize: function () {
        console.log('HELLO');
        console.log(jQuery("html")[0].getAttribute('lang'));
      jQuery.proxyAll(this, /_on/);
      // hack to make leaflet use a particular location to look for images
      this.button = jQuery("#button");
      var html = '<a href="#" class="btn" id="saveClicked">Save</a> <a href="#" class="btn btn-primary" id="publishClicked">Publish</a>';

      this.buttons = jQuery("#saveButtons").html(html);
      //this.buttons.hide();
      this.buttons.show();
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
      resourceData.formatNormalized = this.normalizeFormat(resourceData.format);

      resourceData.url  = this.normalizeUrl(resourceData.url);
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
      var dataset; 
      //, errorMsg;
      //var lang = jQuery("html")[0].getAttribute('lang');
      var lang = jQuery('#reclinetranslate')[0].getAttribute('translation_language');
      console.log('LANG!!!!!!');
      console.log(lang);
          //getAttribute('lang');
      // Datastore
      if (resourceData.datastore_active) {
        if (!("translation_resource" in resourceData)){
            resourceData.backend =  'ckanedit';
        }
        else{
            resourceData.backend =  'ckan';
        }
        // Set endpoint of the resource to the datastore api (so it can locate
        // CKAN DataStore)
        resourceData.endpoint = jQuery('body').data('site-root') + 'api';
         
        resourceData.translation_language = lang;
         
        dataset = new recline.Model.Dataset(resourceData);
         
        errorMsg = this.options.i18n.errorLoadingPreview + ': ' + this.options.i18n.errorDataStore;
        
        translate = new TranslateHelper(resourceData, lang); 
        var trans_lang; 
        try{
            trans_lang = JSON.parse(resourceData.has_translations)[lang];
        }
        catch(err) {
            
        }
        var orig_lang = resourceData.resource_language || 'en';
        console.log('trasn');
        console.log(trans_lang);
        console.log(resourceData);
        //resourceData = translate.delete(function() {}, function() { });
        if (orig_lang == lang){
            alert('Cannot translate in origin language');
        }
        else if (trans_lang === undefined  && !("translation_resource" in resourceData)){
            //translate.create(self.onLoad, self.onComplete);   
            // perform this in a function that starts with _on in order to reproxy
            resourceData = translate.create(function() {}, function() { 
                //window.location.reload() 
                self._onCreateNew(dataset, resourceData)
            });
        }
        else{

        var translationResource = null;
        this.initializeDataset(dataset, resourceData);
        }
      } 
      // CSV/XLS
      else if (resourceData.formatNormalized in {'csv': '', 'xls': ''}) {
        resourceData.format = resourceData.formatNormalized;
        resourceData.backend = 'dataproxy';
        dataset = new recline.Model.Dataset(resourceData);
        //console.log(dataset);
        errorMsg = this.options.i18n.errorLoadingPreview + ': ' +this.options.i18n.errorDataProxy;
        dataset.fetch()
          .done(function(dataset){
            dataset.bind('query:fail', function (error) {
              console.log('error');
              console.log(error);
              jQuery('.data-view-container', self.el).hide();
              jQuery('.header', self.el).hide();
            });
            self.initializeDataExplorer(dataset);
          })
          .fail(function(error){
            if (error.message) errorMsg += ' (' + error.message + ')';
            showError(errorMsg);
          });
      }
    },
    _onCreateNew: function(dataset, resourceData) {
        var translationResource = null;
        this.initializeDataset(dataset, resourceData);
        console.log('create new');
        console.log(resourceData);
    },
    initializeDataset: function(dataset, resourceData) {
        var self = this;
        repaint = function(columns){
                var header = jQuery(".data-view-container .slick-header .slick-column-name");
                for (var key in columns){
                    var mode = columns[key];
                //    console.log(col);
                //}
                header.each(function(idx){
                    var col = jQuery(this);
                    console.log(col.text());
                    col.parent().css("background-image", "none"); 
                    col.parent().css("background-color","red");
                    /*if (col.text() == key){
                        console.log('FOUND');
                        console.log(col.parent());
                        if (mode === 'no-translate'){
                            col.parent().css("background-color","red");
                        }
                        else if (mode === 'manual'){
                            col.parent().css("background-color","green");
                        }
                        else if (mode === 'automatic'){
                            col.parent().css("background-color","yellow");
                        }
                        else if (mode === 'transcription'){
                            col.parent().css("background-color","green");
                        }
                        else{
                            col.parent().css("background-color","black");
                        }

                    }
                    */
                });
            }
            };

        onComplete = function(){
            
        //dataExplorer.clearNotifications();
        //var selfi = this;
        var lang = jQuery('#reclinetranslate')[0].getAttribute('translation_language');
        dataExplorer.model.fetch().done(function(dataset){
            console.log('data');
            console.log(dataset);
            var has_translations = dataset.attributes.has_translations;
            var res_id;
            console.log('hastransl');
            console.log(has_translations);
            console.log(lang);
            try{
                console.log('trying');
                res_id = JSON.parse(has_translations)[lang];
            }
            catch(err) {
                
            }
                console.log(res_id);
                console.log(dataset.attributes.endpoint);
                var res =translate.show_resource({endpoint:dataset.attributes.endpoint, id:res_id}).done(function(result){
                    console.log('res');
                    var result = result.result;
                    console.log(result);
                    var columns = {};
                    try{
                        console.log('trying2');
                        columns = JSON.parse(result.translation_columns);
                    }
                    catch(err2){
                        
                    }
                        console.log(columns);
                        console.log('sef');
                        console.log(self);
                        //jQuery(columns).each(function(col, idx){
                });
        });
        //repaint(columns);
    };
    onLoad = function(){
        dataExplorer.notify({message: 'Loading', loader:true, category: 'warning', persist: true});
        //setTimeout(function(){ dataExplorer.model.fetch()}, 3000);
    };

     console.log('!!!! 4');
     function showError(msg){
        msg = msg || _('error loading preview');
        window.parent.ckan.pubsub.publish('data-viewer-error', msg);
      }
        dataset.fetch()
              .done(function(dataset1){
                
                var fields1 = dataset1.fields.models;
                var records1 = dataset1.records.models;
                
                //dataset1['translation_language'] =  LANGUAGE;
                //dataset1['translation_resource'] = JSON.parse(resourceData.has_translations)[LANGUAGE];
                self.initializeDataExplorer(dataset1);
                
                if (("has_translations" in resourceData)){
                        self.buttons.show();
                        dataset.bind('translate-no', function(col){
                            translate.delete(col.name, onLoad, onComplete);

                        });

                        var html = '<div class="modal-header"><a href="#" class="close" data-dismiss="modal">&times;</a> <h3>Tranlate Column Title</h3></div> <div class="modal-body"> <div class="divDialogElements"><label><h4>Column title:</h4></label><input class="medium" id="xlInput" name="xlInput" type="text" /> </div></div></div> <div class="modal-footer"><a href="#" class="btn" id="closeDialog">Cancel</a> <a href="#" class="btn btn-primary" id="okClicked">OK</a> </div>';
                        jQuery("#windowTitleDialog").html(html);
                        
                        jQuery("#closeDialog").on('click',function(){
                                jQuery("#windowTitleDialog").modal('hide');
                            });

                        dataset.bind('title', function(col){

                            jQuery("#windowTitleDialog").modal('show');
                            jQuery("#okClicked").on('click',function(){
                                jQuery("#windowTitleDialog").modal('hide');
                                //var col_translation = jQuery("#xlInput")[0].value;
                                console.log('title???');
                                var col_translation = '';
                                translate.update(col.name, 'title', onLoad, onComplete, col_translation);

                            });
                            
                        });
                        dataset.bind('translate-manual', function(col){
                            jQuery("#windowTitleDialog").modal('show');
                            jQuery("#okClicked").on('click',function(){
                                jQuery("#windowTitleDialog").modal('hide');
                                var col_translation = jQuery("#xlInput")[0].value;
                                translate.update(col.name, 'manual', onLoad, onComplete, col_translation);

                            });


                        });
                        dataset.bind('transcript', function(col){
                            jQuery("#windowTitleDialog").modal('show');
                            jQuery("#okClicked").on('click',function(){
                                jQuery("#windowTitleDialog").modal('hide');
                                var col_translation = jQuery("#xlInput")[0].value;
                                translate.update(col.name, 'transcription', onLoad, onComplete, col_translation);

                            });

                        });
                        dataset.bind('translate-auto', function(col){
                            //TODO
                            //translate.update(resourceData, col.name, 'automatic');
                        });
            
                        dataset1.queryState.bind('save', function(){
                            console.log('dataset being saved...');
                            dataset1.save();
                        });

                        self.save_btn.click(function() {
                            console.log('dataset being saved...');
                            dataset1.save();
                        });

                        self.publish_btn.click(function() {
                            console.log('resource being published...');
                            translate.publish(onLoad, function() { window.top.location.href = resourceData.url.substring(0,resourceData.url.indexOf('resource'))});
                        });

                }
        
          })
          .fail(function(error){
            if (error.message) errorMsg += ' (' + error.message + ')';
            showError(errorMsg);
          });
    },
    
    getEditor: function(column) {

        //var lang = jQuery("html")[0].getAttribute('lang');
        var lang = jQuery('#reclinetranslate')[0].getAttribute('translation_language');
        var extra = '-' + lang;
        var pos = column.name.indexOf(extra);
        if (pos > -1){
            return  Slick.Editors.Text
        }
        else{
            return null;
        }
    },
    
    initializeDataExplorer: function (dataset) {
      var views = [
        {
          id: 'grid',
          label: 'Grid',
          view: new recline.View.SlickGrid({
            model: dataset,
            //model2: dataset2,
            state: { gridOptions: {editable:true, editorFactory: {getEditor:this.getEditor} } }
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
    normalizeFormat: function (format) {
      var out = format.toLowerCase();
      out = out.split('/');
      out = out[out.length-1];
      return out;
    },
    normalizeUrl: function (url) {
      if (url.indexOf('https') === 0) {
        return 'http' + url.slice(5);
      } else {
        return url;
      }
    },
      };
});




