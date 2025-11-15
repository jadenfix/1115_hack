const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.json({ message: '1115_hack server is running!' });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
