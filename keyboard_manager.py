# Keyboard manager per il bot Telegram
# Gestisce la creazione di tastiere inline

class KeyboardManager:
    """Gestisce le tastiere inline per Telegram"""
    
    @staticmethod
    def get_main_keyboard():
        """Tastiera principale"""
        return {
            "inline_keyboard": [
                [
                    {"text": "🟢 Attiva sistema", "callback_data": "enable"},
                    {"text": "🔴 Disattiva sistema", "callback_data": "disable"}
                ],
                [
                    {"text": "📊 Stato sistema", "callback_data": "status"}
                ],
                [
                    {"text": "📹 Sensori", "callback_data": "sensors"},
                    {"text": "⚙️ Impostazioni", "callback_data": "settings"}
                ]
            ]
        }
    
    @staticmethod
    def get_sensors_keyboard(camera_on, audio_on, distance_on):
        """Tastiera per i sensori"""
        return {
            "inline_keyboard": [
                [
                    {"text": f"📸 Camera: {'ON' if camera_on else 'OFF'}", "callback_data": "camera"}
                ],
                [
                    {"text": f"🎤 Audio: {'ON' if audio_on else 'OFF'}", "callback_data": "audio"}
                ],
                [
                    {"text": f"📏 Distanza: {'ON' if distance_on else 'OFF'}", "callback_data": "distance"}
                ],
                [
                    {"text": "⬅️ Indietro", "callback_data": "back"}
                ]
            ]
        }
    
    @staticmethod
    def get_settings_keyboard():
        """Tastiera per le impostazioni"""
        return {
            "inline_keyboard": [
                [
                    {"text": "🔍 Soglia movimento", "callback_data": "motion_threshold"} 
                ],
                [
                    {"text": "🔊 Soglia audio", "callback_data": "audio_threshold"}
                ],
                [
                    {"text": "📐 Soglia distanza", "callback_data": "distance_threshold"}
                ],
                [
                    {"text": "⏱️ Periodo inibizione", "callback_data": "inhibit_threshold"}
                ],
                [
                    {"text": "⬅️ Indietro", "callback_data": "back"}
                ]
            ]
        }
    
    @staticmethod
    def get_threshold_keyboard(threshold_type, min_val, max_val, current_val, step=1):
        """Tastiera per impostazione soglie"""
        return {
            "inline_keyboard": [
                [
                    {"text": "-", "callback_data": f"dec_{threshold_type}_{step}"},
                    {"text": f"{current_val}", "callback_data": "current"},
                    {"text": "+", "callback_data": f"inc_{threshold_type}_{step}"}
                ],
                [
                    {"text": f"Min: {min_val}", "callback_data": f"min_{threshold_type}"},
                    {"text": f"Max: {max_val}", "callback_data": f"max_{threshold_type}"}
                ],
                [
                    {"text": "⬅️ Indietro", "callback_data": "settings"}
                ]
            ]
        }