// RunOpenCV.tsx
import React, { useEffect, useRef } from "react";
import "./RunOpenCV.css"; // import your CSS file

const RunOpenCV: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);

  const getVideo = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    getVideo();
  }, []);

  return (
    <div>
      <video id="input_video" ref={videoRef} className="limitedVideo" />
      <canvas id="output_video" />
    </div>
  );
};

export default RunOpenCV;
