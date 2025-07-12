const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

// API Layer
app.get('/hello', (req, res) => {
  // Controller Layer
  res.json({ message: 'Hello World' });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});