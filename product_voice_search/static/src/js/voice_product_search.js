/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

class VoiceProductSearch extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            listening: false,
            status: "Idle",
            query: "",
            results: [],
            lastUpdated: null,
            supported: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
        });

        this._recognition = null;
        onMounted(() => this._initRecognition());
        onWillUnmount(() => this._cleanupRecognition());
    }

    _initRecognition() {
        const Recog = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!Recog) {
            this.state.status = "Speech recognition not supported in this browser";
            this.state.supported = false;
            return;
        }
        this._recognition = new Recog();
        this._recognition.lang = "en-US";
        this._recognition.continuous = false;
        this._recognition.interimResults = false;

        this._recognition.onstart = () => {
            this.state.listening = true;
            this.state.status = "Listening...";
        };
        this._recognition.onerror = (e) => {
            this.state.listening = false;
            this.state.status = `Error: ${e.error}`;
            this.notification.add(this.state.status, { type: "warning" });
        };
        this._recognition.onend = () => {
            this.state.listening = false;
            if (!this.state.status.startsWith("Error")) {
                this.state.status = "Idle";
            }
        };
        this._recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.state.query = transcript;
            this.state.status = `Heard: "${transcript}"`;
            this._runSearch(transcript);
        };
    }

    _cleanupRecognition() {
        if (this._recognition) {
            this._recognition.onstart = null;
            this._recognition.onend = null;
            this._recognition.onresult = null;
            this._recognition.onerror = null;
            this._recognition.stop();
        }
    }

    toggleListening() {
        if (!this.state.supported || !this._recognition) {
            this.notification.add("Speech recognition not supported in this browser.", { type: "warning" });
            return;
        }
        if (this.state.listening) {
            this._recognition.stop();
        } else {
            try {
                this._recognition.start();
            } catch (e) {
                // start might throw if called too quickly after stop
            }
        }
    }

    onInputChange(ev) {
        this.state.query = ev.target.innerText;
    }

    onInputKeyup(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            const text = ev.target.innerText.trim();
            this._runSearch(text);
        }
    }

    async _runSearch(text) {
        const query = (text || "").trim();
        this.state.query = query;
        if (!query) {
            this.state.results = [];
            this.state.status = "Idle";
            return;
        }
        this.state.status = "Searching...";
        try {
            const records = await this.orm.call("product.product", "tally_product_search", [], {
                search_term: query,
                domain: [],
                limit: 50,
            });
            this.state.results = records.map(([id, name]) => ({ id, name }));
            this.state.lastUpdated = DateTime.now();
            this.state.status = `${records.length} result(s)`;
        } catch (err) {
            this.state.status = "Search failed";
            this.notification.add(err?.message || "Search failed", { type: "danger" });
        }
    }
}

VoiceProductSearch.template = "product_voice_search.ClientAction";

registry.category("actions").add("product_voice_search.client_action", VoiceProductSearch);

export default VoiceProductSearch;
