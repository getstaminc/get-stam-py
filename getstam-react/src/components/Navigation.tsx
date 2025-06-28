import React from "react";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Button from "@mui/material/Button";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import { Link } from "react-router-dom";
import { sports } from "../configs/sportsConfig";

const Navigation: React.FC = () => {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  const handleMoreClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const inSeasonSports = sports.filter((sport) => sport.inSeason);
  const offSeasonSports = sports.filter((sport) => !sport.inSeason);

  return (
    <AppBar position="static">
      <Toolbar>
        {inSeasonSports.map((sport) => (
          <Button
            key={sport.name}
            color="inherit"
            component={Link}
            to={sport.path}
          >
            {sport.name}
          </Button>
        ))}
        {offSeasonSports.length > 0 && (
          <>
            <Button color="inherit" onClick={handleMoreClick}>
              More
            </Button>
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              {offSeasonSports.map((sport) => (
                <MenuItem
                  key={sport.name}
                  component={Link}
                  to={sport.path}
                  onClick={handleClose}
                >
                  {sport.name}
                </MenuItem>
              ))}
            </Menu>
          </>
        )}
      </Toolbar>
    </AppBar>
  );
};

export default Navigation;