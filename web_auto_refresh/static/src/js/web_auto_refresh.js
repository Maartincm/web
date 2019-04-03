(function() {
    openerp.web.WebClient.include({
        declare_bus_channel: function() {
            this._super();
            var self = this,
                channel = "auto_refresh_kanban_list";
            this.bus_on(channel, function(message) {            // generic auto referesh
                model = message[0];
                method = message[1];
                author_id = message[2];
                ids = message[3];
                if (this.action_manager.inner_widget){
                    var active_view = this.action_manager.inner_widget.active_view;
                    if (typeof(active_view) != 'undefined'){   // in mail inbox page, no active view defined
                        var controller = this.action_manager.inner_widget.views[active_view].controller;
                        var action = this.action_manager.inner_widget.action;
                        if (controller.$buttons){
                            if (action.auto_refresh>0 && controller.model == model  && ! controller.$buttons.hasClass('oe_editing')){
                                if (active_view == "kanban" || active_view == "list") {
                                    if (method == 'create' && this.session.uid == author_id) {
                                        return;
                                    }
                                    if (active_view == "kanban"){
                                        controller.do_reload();    // kanban view has do_reload
                                    }
                                    else{
                                        controller.reload();     // list view only has reload
                                    }
                                }
                                if  (active_view == "form") {
                                    cur_id = parseInt(this._current_state.id);
                                    if (ids && cur_id && ids.includes(cur_id)){
                                        controller.reload();
                                    }
                                }
                            }
                        }
                    }
                }
            });
            this.add_bus_channel(channel);
            channel = "mail.notification";
            this.bus_on(channel, function(message) {
                if (!this.action_manager.inner_action) {
                    return;
                }
                var model  = this.action_manager.inner_action.res_model;
                var textarea = $('textarea.field_text')[0];  //check whether in mail compose mode
                if (model === 'mail.message' && typeof(textarea)==='undefined'){
                    if (this.session.uid === message){     // message actually the uid
                        this.action_manager.inner_widget.do_searchview_search();
                    }
                }
            });
            this.add_bus_channel(channel);
        },
    });
})();
