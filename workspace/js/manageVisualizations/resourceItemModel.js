var ResourceItemModel = Backbone.Model.extend({
    defaults: function() {
        return {
            title: "",
            id: "",
            created_at: "",
            category: "",
            author: "",
            status_nice: "",
            dataset_title: "",
            revision_id:"",
            url:""
        };
    },

    remove: function (options) {
        var opts = _.extend({url: 'remove/' + this.id}, options || {});

        return Backbone.Model.prototype.destroy.call(this, opts);
    },

    remove_revision: function (options) {
        var opts = _.extend({url: 'remove/revision/' + this.id}, options || {});

        return Backbone.Model.prototype.destroy.call(this, opts);
    },
});


var ListResources = Backbone.PageableCollection.extend({

  model: ResourceItemModel,
  url: "filter",

  // Any `state` or `queryParam` you override in a subclass will be merged with
  // the defaults in `Backbone.PageableCollection` 's prototype.
  state: {

    // You can use 0-based or 1-based indices, the default is 1-based.
    // You can set to 0-based by setting ``firstPage`` to 0.
    firstPage: 0,

    // Set this to the initial page index if different from `firstPage`. Can
    // also be 0-based or 1-based.

    pageSize:10,

  },

 queryParams: {
    totalPages: null,
    page:null,
    pageSize:"itemxpage"
  },

 parseState: function (resp, queryParams, state, options) {
    return {totalRecords: resp.total_entries};
  },

parseRecords: function (resp) {
    return resp.items;
  },

});

