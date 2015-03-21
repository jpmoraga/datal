var theme2View = Backbone.Epoxy.View.extend({

    el: '#id_themeForm',

    template: null,

    events:{

    },

    initialize: function(){
        this.options.currentView.helpAndTips('show');
        this.template = _.template( $("#id_theme2Template").html() );
        this.initSliderSection();
        this.render();
    },

    render: function(){
        this.$el.html(this.template(this.model.attributes));
        return this;
    },

    save: function(event){
        this.setSliderSection();
        var btn_id = $(event.currentTarget).attr("id")
        var ob={};
        if (btn_id === 'id_save') {
            this.options.currentModel.attributes.config = this.model.toJSON();
            this.options.currentModel.attributes.themeID = '2';
            ob['config'] = this.options.currentModel.attributes.config;
            ob['theme'] = this.options.currentModel.attributes.themeID;
            ob['type'] = 'save';
        } else {
            ob['config'] = this.model.toJSON();
            ob['theme'] = '2';
            ob['type'] = 'preview';
        }
        $.ajax({
            type: 'POST',

            data: {
                'jsonString': saferStringify(ob)
            },
            dataType: 'json',
            beforeSend: function(){
                $("#ajax_loading_overlay").show();
            },
            success: function(response) {
                $("#ajax_loading_overlay").hide();
                if(btn_id==="id_save"){
                    $.gritter.add({
                        title : gettext('ADMIN-HOME-SECTION-SUCCESS-TITLE'),
                        text : gettext('ADMIN-HOME-SECTION-SUCCESS-TEXT'),
                        image : '/media_workspace/images/common/ic_validationOk32.png',
                        sticky : false,
                        time : 3500
                    });
                }
                else{
                    event.preventDefault();
                    var preview_home = response['preview_home']
                    window.open( preview_home,'','width=1024,height=500,resizable=yes,scrollbars=yes');
                }
            },
            error: function(response) {
                $("#ajax_loading_overlay").hide();
                //response = JSON.parse(response.responseText);
                //jQuery.TwitterMessage({type: 'error', message: response.messages.join('. ')});
                $.gritter.add({
                    title : gettext('ADMIN-HOME-SECTION-ERROR-TITLE'),
                    text : gettext('ADMIN-HOME-SECTION-ERROR-TEXT'),
                    image : '/media_workspace/images/common/ic_validationError32.png',
                    sticky : true,
                    time : ''
                });
            },
            url: '/personalizeHome/save/'
        });
    },
    initSliderSection: function(){
        var initialResources = [];
        var resourceQuery='';
        _.each(this.model.get('sliderSection'), function(item, index){
            if (index > 0){
                resourceQuery += " OR ";
            }
            switch (item.type){
                case 'ds':
                    resourceQuery += "(datastream_id:"+ item.id+" AND type:"+item.type+")";
                    break;
                case 'chart':
                    resourceQuery += "(visualization_id:"+ item.id+" AND type:"+item.type+")";
                    break;
            }

        });

        $.when(
                $.ajax({
                    url: "/admin/suggest",
                    type: "GET",
                    dataType: "json",
                    contentType: "application/json; charset=utf-8",
                    data: {term: resourceQuery, resources:['ds','chart']},

                })).done( function(data){
                    $('#id_sourceNameSuggest').taggingSources({
                        source:function(request, response) {
                            /* $.getJSON("/admin/suggest", { term: request.term.concat("*"), resources:['ds','chart']}, response); */
                            $.getJSON("/admin/suggest", { term: request.term.concat("*"), resources:['ds']}, response);
                        }
                        , minLength: 3
                        , sources: data
                    });
                });
    },
    setSliderSection: function(){

        var resourceList = [];
        var $lTags = $('[id*=id_tag][id$=_name]', '#id_source_container .tagsContent' );
        var $lSources = $('#id_source_container .tag');
        var lData = '';
        $lSources.each(function(i){
            var $lSource = $(this).find('.tagTxt');
            lData = $lSource.attr("id").split("_");
            var id = lData[0];
            var type = lData[1];
            var obj = {
                    id: id,
                    type: type
            };
            resourceList.push(obj);
        });
        this.model.set('sliderSection', resourceList)

    }
});