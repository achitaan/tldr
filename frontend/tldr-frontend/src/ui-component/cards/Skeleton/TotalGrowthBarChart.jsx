import React, { useEffect, useRef } from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material.CardContent';
import Grid from '@mui/material/Grid2';
import Typography from '@mui/material/Typography';
import { gridSpacing } from '../../../store/constant';

export default function TotalGrowthBarChart() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const getVideo = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(console.error);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    getVideo();

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
    <Card>
      <CardContent>
        <Grid container spacing={gridSpacing}>
          <Grid size={12}>
            <Typography variant="h3">Camera Feed</Typography>
          </Grid>
          <Grid size={12} sx={{ mt: 2 }}>
            <div className="video-container">
              <video 
                ref={videoRef}
                className="camera-feed"
                playsInline
                style={{
                  width: '100%',
                  maxHeight: '530px',
                  objectFit: 'contain',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '8px'
                }}
              />
              <canvas 
                id="output_video"
                style={{
                  display: 'none'
                }} 
              />
            </div>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}
