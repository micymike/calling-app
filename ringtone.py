import os
import threading
import time
import wave
import pyaudio
from threading import Thread

class RingtonePlayer:
    """Simple audio player for ringtones using PyAudio."""
    
    def __init__(self):
        self.is_playing = False
        self.stop_requested = False
        self.play_thread = None
        self.ringtone_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "call.wav")
        
    def play_ringtone(self):
        """Start playing the ringtone."""
        if self.is_playing:
            return
            
        if not os.path.exists(self.ringtone_path):
            print(f"Ringtone file not found: {self.ringtone_path}")
            return
            
        self.stop_requested = False
        self.is_playing = True
        self.play_thread = Thread(target=self._play_audio_loop, daemon=True)
        self.play_thread.start()
    
    def _play_audio_loop(self):
        """Play the audio file in a loop until stopped."""
        try:
            p = pyaudio.PyAudio()
            
            while not self.stop_requested:
                try:
                    wf = wave.open(self.ringtone_path, 'rb')
                    
                    # Open stream
                    stream = p.open(
                        format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True
                    )
                    
                    # Read and play chunks
                    chunk_size = 1024
                    data = wf.readframes(chunk_size)
                    
                    while data and not self.stop_requested:
                        stream.write(data)
                        data = wf.readframes(chunk_size)
                    
                    # Clean up
                    stream.stop_stream()
                    stream.close()
                    wf.close()
                    
                    # Small pause between loops
                    if not self.stop_requested:
                        time.sleep(0.5)
                        
                except Exception as e:
                    print(f"Error playing ringtone: {e}")
                    break
                    
            p.terminate()
            
        except Exception as e:
            print(f"Ringtone player error: {e}")
        finally:
            self.is_playing = False
            
    def stop_ringtone(self):
        """Stop playing the ringtone."""
        if self.is_playing:
            self.stop_requested = True
            if self.play_thread:
                self.play_thread.join(timeout=1.0)