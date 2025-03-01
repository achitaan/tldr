import React, { useEffect, useRef, useState } from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import { gridSpacing } from '../../../store/constant';

export default function TotalGrowthBarChart() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const getVideo = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        // Important: Wait for the video to be ready
        await videoRef.current.play();
        setIsLoading(false);
      }
    } catch (err) {
      console.error('Camera error:', err);
      setError(err.message);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    getVideo();

    // Cleanup function
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, []); // Empty dependency array means this runs once on mount

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Grid container spacing={gridSpacing}>
          <Grid item xs={12}>
            <Typography variant="h3" color="primary">
              Live Camera Feed
            </Typography>
          </Grid>
          <Grid item xs={12}>
            <div style={{
              position: 'relative',
              width: '100%',
              height: '530px',
              backgroundColor: '#1e1e1e',
              borderRadius: '8px',
              overflow: 'hidden'
            }}>
              {isLoading && (
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  color: 'white'
                }}>
                  <CircularProgress color="primary" />
                </div>
              )}
              {error && (
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  color: 'red',
                  textAlign: 'center'
                }}>
                  <Typography color="error">
                    Camera Error: {error}
                  </Typography>
                </div>
              )}
              <video 
                ref={videoRef}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain'
                }}
                playsInline
                muted
                autoPlay
              />
              <canvas 
                id="output_video"
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
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
