import React from "react";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import MenuIcon from "@mui/icons-material/Menu";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Divider from "@mui/material/Divider";
import styles from "./css/Navigation.module.css";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import { useNavigate, useLocation } from "react-router-dom";
import { sports } from "../configs/sportsConfig";

const TabsNavigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  const inSeasonSports = sports.filter((sport) => sport.inSeason);
  const offSeasonSports = sports.filter((sport) => !sport.inSeason);

  const currentTab = inSeasonSports.findIndex(
    (sport) => location.pathname === sport.path
  );

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    navigate(inSeasonSports[newValue].path);
  };

  const handleMoreClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuItemClick = (path: string) => {
    navigate(path);
    setAnchorEl(null);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  // Drawer handlers
  const toggleDrawer = (open: boolean) => () => {
    setDrawerOpen(open);
  };

  const handleDrawerItemClick = (path: string) => {
    navigate(path);
    setDrawerOpen(false);
  };

  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "transparent" }}>
      {isMobile ? (
        <>
          <IconButton
            edge="start"
            color="inherit"
            aria-label="menu"
            onClick={toggleDrawer(true)}
            sx={{ ml: 1, mt: 1 }}
          >
            <MenuIcon />
          </IconButton>
          <Drawer anchor="left" open={drawerOpen} onClose={toggleDrawer(false)}>
            <Box sx={{ width: 220 }} role="presentation" onClick={toggleDrawer(false)}>
              <List>
                {inSeasonSports.map((sport) => (
                  <ListItem key={sport.name} disablePadding>
                    <ListItemButton onClick={() => handleDrawerItemClick(sport.path)}>
                      <ListItemText primary={sport.name} />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
              <Divider />
              <List>
                {offSeasonSports.map((sport) => (
                  <ListItem key={sport.name} disablePadding>
                    <ListItemButton onClick={() => handleDrawerItemClick(sport.path)}>
                      <ListItemText primary={sport.name} />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Box>
          </Drawer>
        </>
      ) : (
        <>
          <Tabs
            value={currentTab === -1 ? false : currentTab}
            onChange={handleTabChange}
            textColor="primary"
            indicatorColor="primary"
            sx={{
              minHeight: 48,
              "& .MuiTab-root": {
                minHeight: 48,
                textTransform: "none",
                fontWeight: 500,
                color: "black",
                bgcolor: "transparent",
                "&:hover": {
                  borderBottom: "2px solid #1976d2",
                  bgcolor: "transparent",
                },
              },
              "& .Mui-selected": {
                color: "#1976d2",
                fontWeight: 700,
              },
              bgcolor: "transparent",
            }}
          >
            {inSeasonSports.map((sport) => (
              <Tab key={sport.name} label={sport.name} />
            ))}
            {offSeasonSports.length > 0 && (
            <Button
              color="inherit"
              disableRipple
              className={styles.moreButton}
              onClick={handleMoreClick}
            >
              More
            </Button>
            )}
          </Tabs>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleClose}
          >
            {offSeasonSports.map((sport) => (
              <MenuItem
                key={sport.name}
                onClick={() => handleMenuItemClick(sport.path)}
              >
                {sport.name}
              </MenuItem>
            ))}
          </Menu>
        </>
      )}
    </Box>
  );
};

export default TabsNavigation;