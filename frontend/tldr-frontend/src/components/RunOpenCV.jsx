import React, { useEffect, useRef } from "react";
import "./RunOpenCV.css";

const RunOpenCV = () => {
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const getVideo = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        // Wait for the video to be loaded before playing
        await videoRef.current.play().catch(console.error);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    getVideo();

    // Cleanup function to stop the stream when component unmounts
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, []);

  return (
    <div>
      <video 
        id="input_video" 
        ref={videoRef} 
        className="limitedVideo"
        playsInline
      />
      <canvas id="output_video" />
    </div>
  );
};

export default RunOpenCV;