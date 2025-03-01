import PropTypes from 'prop-types';
import React, { useState } from 'react';

// material-ui
import {
  CardContent,
  TextField,
  Typography,
  IconButton,
  Grid,
  Box,
  Divider,
  Button
} from '@mui/material';

// project imports
import MainCard from '../../../ui-component/cards/MainCard';
import SkeletonPopularCard from '../../../ui-component/cards/Skeleton/PopularCard';

// assets
import SendIcon from '@mui/icons-material/Send';

export default function PopularCard({ isLoading }) {
  const [messages, setMessages] = useState([
    { text: 'Welcome to TLDR Chat!', sender: 'bot' },
    { text: 'How can I help you today?', sender: 'bot' }
  ]);
  const [newMessage, setNewMessage] = useState('');

  const handleSendMessage = () => {
    if (newMessage.trim()) {
      setMessages([...messages, { text: newMessage, sender: 'user' }]);
      setNewMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <>
      {isLoading ? (
        <SkeletonPopularCard />
      ) : (
        <MainCard>
          <CardContent sx={{ p: 2, height: '500px', display: 'flex', flexDirection: 'column' }}>
            {/* Chat Header */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="h4">TLDR Chat</Typography>
              <Divider sx={{ mt: 1 }} />
            </Box>

            {/* Messages Area */}
            <Box sx={{ 
              flexGrow: 1, 
              overflowY: 'auto',
              mb: 2,
              display: 'flex',
              flexDirection: 'column',
              gap: 1,
              p: 1
            }}>
              {messages.map((message, index) => (
                <Box
                  key={index}
                  sx={{
                    alignSelf: message.sender === 'user' ? 'flex-end' : 'flex-start',
                    maxWidth: '80%',
                    backgroundColor: message.sender === 'user' ? 'primary.light' : 'grey.100',
                    borderRadius: 2,
                    p: 1
                  }}
                >
                  <Typography>{message.text}</Typography>
                </Box>
              ))}
            </Box>

            {/* Input Area */}
            <Grid container spacing={1} alignItems="center">
              <Grid item xs>
                <TextField
                  fullWidth
                  multiline
                  maxRows={4}
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  variant="outlined"
                  size="small"
                />
              </Grid>
              <Grid item>
                <IconButton 
                  color="primary" 
                  onClick={handleSendMessage}
                  disabled={!newMessage.trim()}
                >
                  <SendIcon />
                </IconButton>
              </Grid>
            </Grid>
          </CardContent>
        </MainCard>
      )}
    </>
  );
}

PopularCard.propTypes = {
  isLoading: PropTypes.bool
};
