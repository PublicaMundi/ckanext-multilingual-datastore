// API calls helpers 
//

//this.TranslateApiHelper = this.TranslateApiHelper || {};

//(function ($, my) {
function TranslateHelper (resource, lang){

//this.TranslateApiHelper = function(resource) {

//erializeCSV= function(dataToSerialize, options) {
//this.ckan.module('reclinepreview', function (jQuery, _) {
    this.resource;
    this.lang;
    this.initialize = function (resource, lang) {
        this.resource = resource;
        this.lang = lang; 
        console.log('HELP');
        console.log(this.lang);
      //jQuery.proxyAll(this, /_on/);
      //this.el.ready(this._onReady);
      // hack to make leaflet use a particular location to look for images
      //L.Icon.Default.imagePath = this.options.site_url + 'vendor/leaflet/0.4.4/images';
      //this.button = jQuery("#button");      
    };
    this.create = function(ld, cb) {
        console.log('creating..');
        console.log(resource);
        var url = resource.endpoint + '/3/action/translate_resource_create';
        
        var package_id = this._strip_package_id(resource.url);
        console.log(package_id);
        var options = {
            resource_id:resource.id,
            package_id: package_id,
            language: lang,

        }
        return this.call_ajax(url, options, ld, cb);    
    };
    this.update = function(col_name, mode, ld, cb, col_translation) {
        var col_translation = col_translation || null;
        console.log('updating..');
        console.log(resource);
        console.log(col_name);
        var self = this;
        var url = resource.endpoint + '/3/action/translate_resource_update';
        
        //var translations = JSON.parse(resource.has_translations);
        var translations = {};
        try{
            translations = JSON.parse(resource.has_translations);
        }
        catch(err) {
            alert(err);
        }

        console.log(translations);
        var new_res_id = translations[lang];
        // Check if column exists to warn user
        var res = {endpoint:resource.endpoint, id:new_res_id};
        var upd_res = this.show(res, function(res){
            console.log('show success');
            console.log(res);
            res = res.responseJSON;
            if (res.success){
                console.log('answer ok');
                var fields = res.result.fields;
                var field_exists = false; 
                fields.forEach(function(fld, idx){
                    if (fld.id == col_name){
                        field_exists = true;
                        return;
                    }
                });
                /*if (mode === 'title'){
                        var options = {
                                resource_id: new_res_id,
                                column_name: col_name,
                                mode: mode,
                                translation: col_translation,
                            }
                            return self.call_ajax(url, options, ld, cb); 
                }*/

                if (field_exists){
                            var html = '<div class="modal-header"><a href="#" class="close" data-dismiss="modal">&times;</a> <h3>Please Confirm Action</h3></div> <div class="modal-body"> <label>Column is already translated. Are you sure you want to override?</label> </div> <div class="modal-footer"><a href="#" class="btn" id="closeDialog">Cancel</a> <a href="#" class="btn btn-primary" id="okClicked">OK</a> </div>';

                            jQuery("#windowTitleDialog").html(html);
                            jQuery("#windowTitleDialog").modal('show');
                            //var name = string;
                            var ncolumn;
                            jQuery("#closeDialog").on('click', function(){
                                jQuery("#windowTitleDialog").modal('hide');
                            });
                            jQuery("#okClicked").on('click',function(){
                                jQuery("#windowTitleDialog").modal('hide');
                                // Update column
                                var options = {
                                    resource_id: new_res_id,
                                    column_name: col_name,
                                    mode: mode,
                                    translation: col_translation,
                                }
                                return self.call_ajax(url, options, ld, cb); 
                                });
                        
                        return;
                    }
                    else {
                                var options = {
                                    resource_id: new_res_id,
                                    column_name: col_name,
                                    mode: mode,
                                    translation: col_translation,
                                }
                                return self.call_ajax(url, options, ld, cb); 
                    }
        //});
        
        console.log(new_res_id);
        }
        
        });
        
    };
    this.call_ajax = function(url, options, ld, cb) {
        return $.ajax({
            type: "POST",
            url: url,
            data: JSON.stringify(options),
            dataType: 'json',
            async: true,
            beforeSend: ld,
            complete: cb,
            //function(response) {
            //    if (dataExplorer !== undefined){
                //dataExplorer.clearNotifications();
            //    console.log('complete');
            //    console.log(dataExplorer);
                //dataExplorer.model.fetch();
            //    }

                //$('.loading-spinner').css({'display':'none'});
                //alert('Completed');
            //},
            success: function(response) {
                console.log('succeeded');
                console.log(response);
            },
            failure: function(response) {
                console.log('failed');
                console.log(response);
            },
            error: function(response) {
                //if (response.status == 409){
                //    return;
                //}
                console.log('error');
                console.log(response);
                alert('Error: .\n' + response.status + ':' + response.responseText);
            },
        });
    };
    this.delete = function(col_name, ld, cb) {
        console.log('deleting..');
        console.log(resource);
        console.log(col_name);
        var self = this;

        var url = resource.endpoint + '/3/action/translate_resource_delete';
        
        //var translations = JSON.parse(resource.has_translations);
        var translations = {};
        try{
            translations = JSON.parse(resource.has_translations);
        }
        catch(err) {
            alert(err);
        }
        var new_res_id = translations[lang];
        
        if (col_name !== undefined){
        
        var options = {
            resource_id: new_res_id,
            column_name: col_name
        }
        
        var html = '<div class="modal-header"><a href="#" class="close" data-dismiss="modal">&times;</a> <h3>Please Confirm Action</h3></div> <div class="modal-body"> <label>Column is already translated. Are you sure you want to delete it?</label> </div> <div class="modal-footer"><a href="#" class="btn" id="closeDialog">Cancel</a> <a href="#" class="btn btn-primary" id="okClicked">OK</a> </div>';
        }
        else{
            var options = {
                resource_id: new_res_id
            }
        
        var html = '<div class="modal-header"><a href="#" class="close" data-dismiss="modal">&times;</a> <h3>Please Confirm Action</h3></div> <div class="modal-body"> <label>Are you sure you want to delete all translations for this language?</label> </div> <div class="modal-footer"><a href="#" class="btn" id="closeDialog">Cancel</a> <a href="#" class="btn btn-primary" id="okClicked">OK</a> </div>';
        }


        jQuery("#windowTitleDialog").html(html);
        jQuery("#windowTitleDialog").modal('show');
        //var name = string;
        var ncolumn;
        jQuery("#closeDialog").on('click', function(){
            jQuery("#windowTitleDialog").modal('hide');
        });
        jQuery("#okClicked").on('click',function(){
            jQuery("#windowTitleDialog").modal('hide');

            return self.call_ajax(url, options, ld, cb);    
        });
    },
    this.publish = function(ld, cb) {
        console.log('publishing..');
        console.log(resource);
        var url = resource.endpoint + '/3/action/translate_resource_publish';
        
        var translations = {};
        try{
            translations = JSON.parse(resource.has_translations);
        }
        catch(err) {
            alert(err);
        }
        
        var new_res_id = translations[lang];

        var options = {
            resource_id:new_res_id,
        }
        return this.call_ajax(url, options, ld, cb);    
    };

    this.show =  function(resource, cb) {
        console.log('showing..');
        console.log(resource.id);

        var url = resource.endpoint + '/3/action/datastore_search';
        
        var options = {
            id: resource.id,
        }
        return $.ajax({
                type: "POST",
                url: url,
                data: JSON.stringify(options),
                dataType: 'json',
                async: true, 
                complete: cb,
        });    
    };

    this.show_resource =  function(resource, cb) {
        console.log('showing..');
        console.log(resource.id);

        var url = resource.endpoint + '/3/action/resource_show';
        var options = {
            id: resource.id,
        }
        return $.ajax({
                type: "POST",
                url: url,
                data: JSON.stringify(options),
                dataType: 'json',
                async: true,
                complete: cb,
        });    
    };

    this._strip_package_id = function(url) {
        // CKAN 2.2 doesnt provide package_id in resource_show
        // strip it from url
        var str = "dataset/";
        var start = url.indexOf(str)+str.length;
        var str = "/resource";
        var end = url.indexOf(str);
        return url.substring(start, end);

    };
    


};

//})(my, jQuery);



