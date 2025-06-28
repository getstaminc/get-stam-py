// import React from 'react';
// import logo from './logo.svg';
// import './App.css';

// function App() {
//   return (
//     <div className="App">
//       <header className="App-header">
//         <img src={logo} className="App-logo" alt="logo" />
//         <p>
//           Edit <code>src/App.tsx</code> and save to reload.
//         </p>
//         <a
//           className="App-link"
//           href="https://reactjs.org"
//           target="_blank"
//           rel="noopener noreferrer"
//         >
//           Learn React
//         </a>
//       </header>
//     </div>
//   );
// }

// export default App;

import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TabsNavigation from "./components/TabsNavigation";

function App() {
  return (
    <Router>
      <Box sx={{ textAlign: "center", mt: 2, mb: 1 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, color: "#1976d2" }}>
          get<span style={{ fontWeight: 400 }}>STAM</span>
        </Typography>
        <Typography variant="subtitle1" sx={{ color: "#555" }}>
          Stats That Actually Matter
        </Typography>
      </Box>
      <TabsNavigation />
      {/* Your routes here */}
    </Router>
  );
}

export default App;
