import time
import pyb
import audio
import logger
import gc
from ulab import numpy as np
from ulab import utils

# LED for debugging
green_led = pyb.LED(2)
red_led = pyb.LED(1)

# Global variable for the AudioDetector instance
global_audio_detector = None

# Global callback function for audio
def global_audio_callback(buf):
    global global_audio_detector
    if global_audio_detector:
        global_audio_detector.process_audio(buf)

class AudioDetector:
    def __init__(self, config):
        """Initialize audio detector with improved peak detection"""
        global global_audio_detector
        global_audio_detector = self  # Assign this instance to the global variable

        self.config = config
        self.audio_enabled = False
        self.audio_streaming_active = False
        self.raw_buf = None

        # Improved peak detection parameters
        self.sound_detected = False  # Flag for sound detection
        self.last_level = 0          # Store last detected level
        self.peak_count = 0          # Counter for detected peaks
        self.last_alert_time = 0     # Time of last alert

        # Parameters from config, with proper defaults if not available
        self.reset_threshold = 5     # Level below which we consider the sound has ended
        self.min_time_between_alerts = self.config.INHIBIT_PERIOD # Minimum seconds between alerts

        # Initialize audio system
        self.init_audio()

    def init_audio(self):
        """Initialize audio with appropriate settings"""
        logger.info("Initializing audio detector with improved peak detection...")

        try:
            # Initialize audio with the configured gain
            audio.init(channels=1, frequency=16000, gain_db=self.config.AUDIO_GAIN, highpass=0.9883)
            self.audio_enabled = True
            logger.info(f"Audio initialized with gain {self.config.AUDIO_GAIN}dB")

            # Initialize the buffer for FFT analysis
            self.raw_buf = None

            # Reset detection state
            self.sound_detected = False
            self.peak_count = 0

            # Force a garbage collection
            gc.collect()

        except Exception as e:
            logger.error(f"Audio initialization error: {e}")

    def process_audio(self, buf):
        """Process audio buffer using peak detection algorithm"""
        # Store the buffer for analysis
        if not self.raw_buf:
            self.raw_buf = buf

        # Skip processing if disabled or not active
        if not self.audio_enabled or not self.audio_streaming_active:
            return

        try:
            if self.raw_buf:
                # Convert buffer to int16 array for analysis
                pcm_buf = np.frombuffer(self.raw_buf, dtype=np.int16)
                self.raw_buf = None  # Reset buffer immediately to allow new data

                # Skip processing if buffer is empty
                if len(pcm_buf) == 0:
                    return

                # Calculate FFT spectrum (useful for frequency analysis if needed)
                fft_buf = utils.spectrogram(pcm_buf)

                # IMPROVED: Calculate peak amplitude instead of average
                peak_amplitude = np.max(abs(pcm_buf))
                peak_level = int((peak_amplitude / 32768) * 100)

                # Store raw level for reference
                raw_level = int((np.mean(abs(pcm_buf)) / 32768) * 100)

                # Store the level for external access
                self.last_level = peak_level

                # Debug logging
                if self.config.DEBUG and time.time() % 5 == 0:
                    logger.debug(f"Audio peak: {peak_level}, raw: {raw_level}, threshold: {self.config.SOUND_THRESHOLD}", verbose=True)

                # Check for peak detection
                if peak_level > self.config.SOUND_THRESHOLD:
                    self._handle_audio_peak(peak_level)
                elif peak_level < self.reset_threshold and self.sound_detected:
                    # Reset the detection state when audio falls below reset threshold
                    self.sound_detected = False
                    red_led.off()  # Visual indication of reset

        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
            # Force garbage collection
            gc.collect()

    def _handle_audio_peak(self, level):
        """Handle detected audio peak with improved management"""
        current_time = time.time()

        # Check if enough time has passed since last alert
        if current_time - self.last_alert_time >= self.min_time_between_alerts:
            # Increment peak counter
            self.peak_count += 1

            # Set detection flag
            self.sound_detected = True

            # Log the detection
            logger.info(f"Sound peak #{self.peak_count} detected: level={level}, threshold={self.config.SOUND_THRESHOLD}")

            # Visual feedback
            red_led.on()

            # Update last alert time
            self.last_alert_time = current_time

            # No need to return anything - the main system checks status with check_sound()

    def check_sound(self):
        """Check if sound has been detected, returning detection state and level"""
        if self.sound_detected:
            # We return the detection but don't reset it here - that happens when
            # audio level drops below reset_threshold in process_audio
            return True, self.last_level
        return False, 0

    def start_audio_detection(self):
        """Start audio detection with proper initialization"""
        if not self.audio_enabled:
            logger.warning("Audio not available for detection")
            return False

        try:
            # Reset detection state
            self.sound_detected = False
            self.raw_buf = None

            # Start audio streaming
            audio.start_streaming(global_audio_callback)
            self.audio_streaming_active = True
            logger.info("Audio streaming started with improved peak detection")
            return True
        except Exception as e:
            logger.error(f"Error starting audio streaming: {e}")
            self.audio_streaming_active = False
            return False

    def stop_audio_detection(self):
        """Stop audio detection safely"""
        try:
            # First mark streaming as inactive to block new callbacks
            self.audio_streaming_active = False

            # Short delay for in-flight callbacks to complete
            time.sleep(0.1)

            # Stop the streaming
            audio.stop_streaming()

            # Reset state
            self.sound_detected = False
            self.raw_buf = None

            # Turn off LED if it was on
            red_led.off()

            # Force garbage collection
            gc.collect()

            logger.info("Audio streaming stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping audio streaming: {e}")
            return False

    def recalibrate(self):
        """Reset audio detection (similar to distance recalibration)"""
        try:
            logger.info(f"Recalibrating audio detector. Current threshold: {self.config.SOUND_THRESHOLD}")

            # Reset detection state
            self.sound_detected = False
            self.raw_buf = None

            # Reset peak counter (optional - could keep for long-term stats)
            # self.peak_count = 0

            # Turn off LED if it was on
            red_led.off()

            # Visual feedback for recalibration
            green_led.on()
            time.sleep(0.05)
            green_led.off()

            logger.info(f"Audio detector recalibrated with threshold: {self.config.SOUND_THRESHOLD}")
            return True
        except Exception as e:
            logger.error(f"Error recalibrating audio detector: {e}")
            return False
