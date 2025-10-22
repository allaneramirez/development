/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

export class SignatureDialog extends Component {
    static template = "custom_report_signature.SignatureDialog";
    static components = { Dialog };
    static props = { report_id: Number, company_id:Number };

    setup() {
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.state = useState({
            imagen: "",
            firma1_name: "",
            firma2_name: "",
        });
    onWillStart(async () => {
      await this.loadData();
    });

    }

    async loadData(){

        const [record] = await this.orm.searchRead(
                "custom.report.signature",
                [
                    ["report_id", "=", this.props.report_id],
                    ["company_id", "=", this.props.company_id],
                ],
                ["imagen",  "firma1", "firma2"]
            );


            if (record) {
                this.state.imagen = record.imagen || "";
                this.state.firma1_name = record.firma1 || "";
                this.state.firma2_name = record.firma2 || "";
            }


    }

    async onInputImagen(ev) {
        const file = ev.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.state.imagen = e.target.result;
            };
            reader.readAsDataURL(file);
        }
    }

    async onSearchUser(ev, target) {
        const name = ev.target.value;
        console.log(name,"name")
        const users = await this.orm.call("res.users", "name_search", [name], {
            context: { active_test: false },
        });
        if (target === "firma1") {

            this.state.firma1_name = name;

        } else {
            this.state.firma2_name = name;

        }
    }

    cancel() {

        this.props.close();

    }

    get imagen() {
    return this.state.imagen;
}

    async save() {
        await this.orm.call("custom.report.signature", "create_or_update_signature", [{
            company_id: this.props.company_id,
            report_id: this.props.report_id,
            imagen: this.state.imagen,
            firma1: this.state.firma1_name,
            firma2: this.state.firma2_name,
        }]);
        this.props.close();


    }
}
