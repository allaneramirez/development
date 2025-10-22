/** @odoo-module **/

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { SignatureDialog } from "@sign_account_report/signatureDialog/signatureDialog";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";
import { AccountReportController } from "@account_reports/components/account_report/controller";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { session } from "@web/session";

patch(AccountReport.prototype, {
    setup() {
        super.setup();  // Ejecuta el setup original

        onWillStart(async () => {
            // Esperar que el controlador haya cargado sus datos
            await this.controller.load(this.env);
            console.log( this)
//            TODO ID DINAMICO DESDE CONFIGURACIONES DEL REPORTE
            if (this.props.action?.context?.report_id == 20){
                this.controller.buttons.push({
                    name: "Insertar Firmas",
                    sequence: 999,
                    always_show: true,
                    custom_handler: true,
                    disabled: false,
                });
            }

        });
    },
});

patch(AccountReportController.prototype, {
    setup() {
        super.setup?.();
        this.dialog = useService("dialog");
        this.companyService = useService("company");

    },

    buttonAction(ev, button) {
        const report_id = this.action.context.report_id
        const company_id = this.data.context.allowed_company_ids[0]
        console.log(company_id,"action!!")

        if (button.custom_handler) {
            ev?.preventDefault();
            ev?.stopPropagation();
            this.dialog.add(SignatureDialog, {
                report_id,
                company_id
            });
        } else {
            return super.buttonAction(ev, button);
        }
    },
});