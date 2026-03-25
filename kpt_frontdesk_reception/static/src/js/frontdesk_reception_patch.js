/** @odoo-module **/

import { Frontdesk } from "@frontdesk/frontdesk";
import { VisitorForm } from "@frontdesk/visitor_form/visitor_form";
import { patch } from "@web/core/utils/patch";
import { onWillUnmount, useRef, useState } from "@odoo/owl";

patch(Frontdesk.prototype, {
    async createVisitor() {
        const result = await this.rpc(`${this.frontdeskUrl}/prepare_selfie_visitor_data`, {
            name: this.visitorData.visitorName,
            phone: this.visitorData.visitorPhone,
            email: this.visitorData.visitorEmail,
            company: this.visitorData.visitorCompany,
            host_ids: this.hostData ? [this.hostData.hostId] : [],
            selfie_image: this.visitorData.visitorSelfie || false,
        });
        this.visitorId = result.visitor_id;
    },

    setVisitorData(name, phone, email, company, selfieImage = false) {
        this.visitorData = {
            visitorName: name,
            visitorPhone: phone,
            visitorEmail: email,
            visitorCompany: company,
            visitorSelfie: selfieImage,
        };
    },
});

patch(VisitorForm.prototype, {
    setup() {
        super.setup(...arguments);
        this.selfieVideoRef = useRef("kptSelfieVideo");
        this.selfieCanvasRef = useRef("kptSelfieCanvas");
        this.selfieState = useState({
            errorMessage: "",
            isCameraOpen: false,
            previewImage: this.props.visitorData?.visitorSelfie
                ? `data:image/jpeg;base64,${this.props.visitorData.visitorSelfie}`
                : false,
            selfieBinary: this.props.visitorData?.visitorSelfie || false,
        });
        this.selfieStream = null;

        onWillUnmount(() => this._stopSelfieStream());
    },

    async openSelfieCamera() {
        if (!navigator.mediaDevices?.getUserMedia) {
            this.selfieState.errorMessage = "Camera is not supported on this device. Upload a photo instead.";
            return;
        }
        try {
            this._stopSelfieStream();
            this.selfieStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "user" },
                audio: false,
            });
            this.selfieState.isCameraOpen = true;
            this.selfieState.errorMessage = "";
            this.selfieVideoRef.el.srcObject = this.selfieStream;
            await this.selfieVideoRef.el.play();
        } catch {
            this.selfieState.errorMessage =
                "Camera access was denied. You can still upload a selfie from this device.";
        }
    },

    captureSelfie() {
        if (!this.selfieVideoRef.el?.videoWidth) {
            this.selfieState.errorMessage = "The camera is not ready yet. Please try again.";
            return;
        }
        const canvas = this.selfieCanvasRef.el;
        const video = this.selfieVideoRef.el;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
        this.selfieState.previewImage = dataUrl;
        this.selfieState.selfieBinary = dataUrl.split(",")[1];
        this.selfieState.errorMessage = "";
        this._stopSelfieStream();
    },

    clearSelfie() {
        this.selfieState.previewImage = false;
        this.selfieState.selfieBinary = false;
        this.selfieState.errorMessage = "";
        this._stopSelfieStream();
    },

    onSelfieFileChange(ev) {
        const [file] = ev.target.files;
        if (!file) {
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            const dataUrl = reader.result;
            this.selfieState.previewImage = dataUrl;
            this.selfieState.selfieBinary = dataUrl.split(",")[1];
            this.selfieState.errorMessage = "";
            this._stopSelfieStream();
        };
        reader.readAsDataURL(file);
        ev.target.value = "";
    },

    _stopSelfieStream() {
        if (this.selfieStream) {
            for (const track of this.selfieStream.getTracks()) {
                track.stop();
            }
            this.selfieStream = null;
        }
        if (this.selfieVideoRef.el) {
            this.selfieVideoRef.el.srcObject = null;
        }
        this.selfieState.isCameraOpen = false;
    },

    _onSubmit() {
        this.props.setVisitorData(
            this.inputNameRef.el.value,
            this.inputPhoneRef.el?.value || false,
            this.inputEmailRef.el?.value || false,
            this.inputCompanyRef.el?.value || false,
            this.selfieState.selfieBinary || false
        );
        this.props.stationInfo.host_selection
            ? this.props.showScreen("HostPage")
            : this.props.showScreen("RegisterPage");
    },
});
