import PropTypes from 'prop-types';
import React, { useEffect, useRef, useState } from 'react';

// material-ui
import { useTheme } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';

// project imports
import MainCard from '../../../ui-component/cards/MainCard';
import EarningCard from './EarningCard';
import { gridSpacing } from '../../../store/constant';

export default function TotalGrowthBarChart({ isLoading: parentIsLoading }) {
  const theme = useTheme();
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const getVideo = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 1920 },   
          height: { ideal: 1080 }
        } 
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        // Wait for loadedmetadata before playing
        await new Promise((resolve) => {
          videoRef.current.onloadedmetadata = resolve;
        });
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
    <>
      <MainCard>
        <Grid container spacing={gridSpacing}>
          <Grid item xs={12}>
          </Grid>
          <Grid item xs={12}>
            <div style={{
              position: 'relative',
              width: '100%',
              height: '600px',
              backgroundColor: theme.palette.mode === 'dark' ? '#1e1e1e' : '#f5f5f5',
              borderRadius: theme.shape.borderRadius,
              overflow: 'hidden',
              boxShadow: theme.shadows[5]
            }}>
              {(isLoading || parentIsLoading) && (
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  zIndex: 2
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
                  zIndex: 2
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
                  objectFit: 'cover',
                  transition: 'opacity 0.3s ease',
                  opacity: isLoading ? 0 : 1
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
      </MainCard>
      <EarningCard videoRef={videoRef} />
    </>
  );
}

TotalGrowthBarChart.propTypes = {
  isLoading: PropTypes.bool
};
