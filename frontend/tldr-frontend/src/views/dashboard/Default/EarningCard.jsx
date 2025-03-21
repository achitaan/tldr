import PropTypes from 'prop-types';
import React, { useState } from 'react';

// material-ui
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import CameraIcon from '@mui/icons-material/Camera';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';

// project imports
import MainCard from '../../../ui-component/cards/MainCard';

export default function EarningCard({ videoRef }) {
  const theme = useTheme();
  const [uploading, setUploading] = useState(false);
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('success');
  const [gptResponse, setGptResponse] = useState('');
  const canvasRef = React.useRef(document.createElement('canvas'));

  const captureImage = async () => {
    if (!videoRef?.current?.srcObject) {
        setSnackbarMessage('Camera not initialized');
        setSnackbarSeverity('error');
        setOpenSnackbar(true);
        return;
    }

    setUploading(true);
    try {
        const video = videoRef.current;
        const canvas = canvasRef.current;

        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        // Draw the current video frame
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert to blob
        const blob = await new Promise((resolve) => {
            canvas.toBlob(resolve, 'image/jpeg', 0.95);
        });

        if (!blob) {
            throw new Error('Failed to capture image');
        }

        // Create form data
        const formData = new FormData();
        formData.append('image', blob, `screenshot-${Date.now()}.jpg`);

        // Send to server
        const response = await fetch('http://localhost:8000/api/images/', {
            method: 'POST',
            body: formData,
            headers: {
                'Accept': 'application/json',
            },
            // Add these options for better error handling
            mode: 'cors',
            credentials: 'include',
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Upload failed: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Screenshot uploaded:', data);
        setGptResponse(data.gpt_response);
        setSnackbarMessage('Screenshot processed successfully!');
        setSnackbarSeverity('success');
    } catch (error) {
        console.error('Error:', error);
        setSnackbarMessage(
            error.message === 'Failed to fetch' 
                ? 'Server is not running. Please start the backend server.' 
                : error.message
        );
        setSnackbarSeverity('error');
    } finally {
        setUploading(false);
        setOpenSnackbar(true);
    }
  };

  const handleCloseSnackbar = (event, reason) => {
    if (reason === 'clickaway') return;
    setOpenSnackbar(false);
  };

  return (
    <MainCard
      sx={{
        bgcolor: theme.palette.mode === 'dark' ? 'secondary.dark' : 'secondary.light',
        color: '#fff',
        p: 0,
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        transition: 'transform 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-3px)'
        }
      }}
    >
      <Box sx={{ p: 2.25 }}>
        <Grid container direction="column" spacing={2}>
          <Grid item>
            <Typography variant="h4" sx={{ color: '#fff' }}>
              Capture Screenshot
            </Typography>
          </Grid>
          <Grid item>
            <Button
              variant="contained"
              startIcon={uploading ? <CircularProgress size={20} color="inherit" /> : <CameraIcon />}
              onClick={captureImage}
              disabled={uploading}
              fullWidth
              sx={{
                bgcolor: 'primary.main',
                color: '#fff',
                py: 1.5,
                '&:hover': {
                  bgcolor: 'primary.dark'
                },
                '&:disabled': {
                  bgcolor: 'rgba(255,255,255,0.12)',
                  color: 'rgba(255,255,255,0.3)'
                }
              }}
            >
              {uploading ? 'Processing...' : 'Take Screenshot'}
            </Button>
          </Grid>
          {gptResponse && (
            <Grid item>
              <Typography 
                variant="body1" 
                sx={{ 
                  color: '#fff',
                  bgcolor: 'rgba(0,0,0,0.1)',
                  p: 2,
                  borderRadius: 1,
                  maxHeight: '200px',
                  overflowY: 'auto'
                }}
              >
                {gptResponse}
              </Typography>
            </Grid>
          )}
        </Grid>
      </Box>
      <Snackbar
        open={openSnackbar}
        autoHideDuration={3000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={snackbarSeverity}
          sx={{ 
            width: '100%',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            '& .MuiAlert-icon': {
              fontSize: '1.5rem'
            }
          }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </MainCard>
  );
}

EarningCard.propTypes = {
  videoRef: PropTypes.shape({
    current: PropTypes.instanceOf(Element)
  }).isRequired
};
