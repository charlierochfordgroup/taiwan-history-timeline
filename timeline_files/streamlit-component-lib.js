// Minimal Streamlit Component Library for vanilla JS v1 components
function sendMessageToStreamlitClient(type, data) {
    var outData = Object.assign({ isStreamlitMessage: true, type: type }, data);
    window.parent.postMessage(outData, "*");
}

var Streamlit = {
    RENDER_EVENT: "streamlit:render",
    events: {
        addEventListener: function(type, callback) {
            window.addEventListener("message", function(event) {
                if (event.data && event.data.type === type) {
                    // Wrap in a CustomEvent-like object so callback gets event.detail.args
                    callback({ detail: event.data });
                }
            });
        }
    },
    setComponentReady: function() {
        sendMessageToStreamlitClient("streamlit:componentReady", { apiVersion: 1 });
    },
    setComponentValue: function(value) {
        sendMessageToStreamlitClient("streamlit:setComponentValue", { value: value });
    },
    setFrameHeight: function(height) {
        sendMessageToStreamlitClient("streamlit:setFrameHeight", { height: height });
    }
};
