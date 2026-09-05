import { createTheme, Theme } from '@mui/material/styles';

const theme: Theme = createTheme({
  palette: {
    primary: {
      main: '#007bff',
    },
  },
  typography: {
    fontFamily: `'Manrope', sans-serif`,
  },
});

export default theme;
