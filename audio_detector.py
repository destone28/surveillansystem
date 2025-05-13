import time
import pyb
import audio
import logger
import gc
from ulab import numpy as np
from ulab import utils

# LED for debugging
green_led = pyb.LED(2)

# Global variable for the AudioDetector instance
global_audio_detector = None

# Global callback function for audio
def global_audio_callback(buf):
    global global_audio_detector
    if global_audio_detector:
        global_audio_detector.process_audio(buf)

class AudioDetector:
    def __init__(self, config):
        """Initialize audio detector with FFT-based analysis"""
        global global_audio_detector
        global_audio_detector = self  # Assign this instance to the global variable
        
        self.config = config
        self.audio_enabled = False
        self.audio_streaming_active = False
        self.raw_buf = None
        self.last_level = 0  # Store last detected level
        self.sound_detected = False  # Flag for sound detection
        
        # Audio analysis variables
        self.avg_levels = []  # For running average of audio levels
        self.max_avg_samples = 5  # Number of samples to keep for averaging
        
        # Initialize audio system
        self.init_audio()
    
    def init_audio(self):
        """Initialize audio with appropriate settings"""
        logger.info("Initializing audio detector with FFT analysis...")

        try:
            # Initialize audio with the configured gain
            audio.init(channels=1, frequency=16000, gain_db=self.config.AUDIO_GAIN, highpass=0.9883)
            self.audio_enabled = True
            logger.info(f"Audio initialized with gain {self.config.AUDIO_GAIN}dB")
            
            # Initialize the buffer for FFT analysis
            self.raw_buf = None
            
            # Reset detection state
            self.sound_detected = False
            self.avg_levels = []
            
            # Force a garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Audio initialization error: {e}")
    
    def process_audio(self, buf):
        """Process audio buffer using FFT analysis"""
        # Store the buffer for FFT analysis
        if not self.raw_buf:
            self.raw_buf = buf
        
        # Skip processing if disabled or already detected
        if not self.audio_enabled or not self.audio_streaming_active or self.sound_detected:
            return
            
        try:
            if self.raw_buf:
                # Convert buffer to int16 array for FFT analysis
                pcm_buf = np.frombuffer(self.raw_buf, dtype=np.int16)
                self.raw_buf = None  # Reset buffer
                
                # Skip processing if buffer is empty
                if len(pcm_buf) == 0:
                    return
                
                # Calculate FFT spectrum
                fft_buf = utils.spectrogram(pcm_buf)
                
                # Calculate audio level - mean of absolute values (0-100 scale)
                level = int((np.mean(abs(pcm_buf)) / 32768) * 100)
                
                # Add to rolling average
                self.avg_levels.append(level)
                if len(self.avg_levels) > self.max_avg_samples:
                    self.avg_levels.pop(0)
                
                # Calculate average level
                avg_level = sum(self.avg_levels) / len(self.avg_levels)
                
                # Scale to match threshold range (convert from 0-100 to threshold range)
                audio_threshold = avg_level * (self.config.SOUND_THRESHOLD_MAX / 100)
                
                # Store the level for external access
                self.last_level = audio_threshold
                
                # Print debug messages
                if self.config.DEBUG and time.time() % 5 == 0:
                    logger.debug(f"Audio level: {audio_threshold:.1f}, threshold: {self.config.SOUND_THRESHOLD}", verbose=True)
                
                # Check if level exceeds threshold
                if audio_threshold > self.config.SOUND_THRESHOLD:
                    logger.info(f"Sound detected: level={audio_threshold:.1f}, threshold={self.config.SOUND_THRESHOLD}")
                    self.sound_detected = True
                    
                    # Visual feedback
                    green_led.on()
                    time.sleep(0.1)
                    green_led.off()
                
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
            # Force garbage collection
            gc.collect()
    
    def check_sound(self):
        """Check if sound has been detected, similar to check_motion() and check_distance()"""
        if self.sound_detected:
            # Reset flag for next detection
            was_detected = True
            self.sound_detected = False
            return was_detected, self.last_level
        return False, 0
    
    def start_audio_detection(self):
        """Start audio detection with proper initialization"""
        if not self.audio_enabled:
            logger.warning("Audio not available for detection")
            return False

        try:
            # Reset detection state
            self.sound_detected = False
            self.avg_levels = []
            self.raw_buf = None
            
            # Start audio streaming
            audio.start_streaming(global_audio_callback)
            self.audio_streaming_active = True
            logger.info("Audio streaming started with FFT analysis")
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
            self.avg_levels = []
            
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
            logger.info("Recalibrating audio detector...")
            
            # Reset detection state
            self.sound_detected = False
            self.avg_levels = []
            
            # Reset buffer
            self.raw_buf = None
            
            return True
        except Exception as e:
            logger.error(f"Error recalibrating audio detector: {e}")
            return False