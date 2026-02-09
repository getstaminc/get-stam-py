import React from "react";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
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
  const [anchorSport, setAnchorSport] = React.useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  const inSeasonSports = sports.filter((sport) => sport.inSeason);
  const offSeasonSports = sports.filter((sport) => !sport.inSeason);

  const currentTab = inSeasonSports.findIndex((sport) => {
    if (location.pathname === sport.path) return true;
    if (sport.leagues && sport.leagues.some((l) => location.pathname === l.path)) return true;
    return false;
  });

  // suppression flag to prevent Tabs onChange navigation when a Tab is clicked to open a menu
  const [suppressNextChange, setSuppressNextChange] = React.useState(false);

  // const handleTabChange = (event: React.SyntheticEvent | null, newValue: number) => {
  //   if (suppressNextChange) {
  //     setSuppressNextChange(false);
  //     return;
  //   }
  //   const sport = inSeasonSports[newValue];
  //   const native = (event as React.SyntheticEvent)?.nativeEvent as any;
  //   if (sport.leagues && sport.leagues.length > 0) {
  //     // navigate only for keyboard Enter/Space
  //     if (native && (native.key === "Enter" || native.key === " ")) {
  //       navigate(sport.leagues[0].path);
  //     }
  //     return;
  //   }
  //   navigate(sport.path);
  // };
  // ...existing code...
  const handleTabChange = (event: React.SyntheticEvent | null, newValue: number) => {
    if (suppressNextChange) {
      setSuppressNextChange(false);
      return;
    }

    const sport = inSeasonSports[newValue];
    if (!sport) return;

    const native = (event as React.SyntheticEvent)?.nativeEvent as any;

    // If the sport has child leagues, only navigate on keyboard Enter/Space to the first league
    if (sport.leagues && sport.leagues.length > 0) {
      if (native && (native.key === "Enter" || native.key === " ")) {
        navigate(sport.leagues[0].path);
      }
      return;
    }

    // Only navigate when a path is defined (path is optional for group headers)
    if (sport.path) {
      navigate(sport.path);
    }
  };

  const handleMoreClick = (event: React.MouseEvent<HTMLButtonElement>) => setAnchorEl(event.currentTarget);
  const handleMenuItemClick = (path?: string) => {
    if (!path) return;
    navigate(path);
    setAnchorEl(null);
    setAnchorSport(null);
  };
  const handleClose = () => { setAnchorEl(null); setAnchorSport(null); };
  const toggleDrawer = (open: boolean) => () => setDrawerOpen(open);
  const handleDrawerItemClick = (path?: string) => {
    if (!path) return;
    navigate(path);
    setDrawerOpen(false);
  };

  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "transparent", display: "flex", alignItems: "center" }}>
      <Box sx={{ flex: 1 }}>
        {isMobile ? (
          <>
            <Button
              variant="outlined"
              color="inherit"
              disableRipple
              aria-label="more-sports"
              onClick={toggleDrawer(true)}
              sx={{
                ml: 1,
                mt: 1,
                mb: 1,
                textTransform: 'none',
                fontWeight: 600,
                borderRadius: 2,
                px: 2,
                color: '#333', // dark text for contrast
                borderColor: '#e0e0e0', // lighter grey border
                bgcolor: 'transparent',
                '&:hover': {
                  bgcolor: '#f5f5f5', // subtle light grey on hover
                  borderColor: '#bdbdbd', // slightly darker on hover
                },
              }}
            >
              MORE SPORTS
            </Button>
            <Drawer anchor="left" open={drawerOpen} onClose={toggleDrawer(false)}>
              <Box sx={{ width: 260, pt:3, px:1 }} role="presentation">
                <List>
                  {inSeasonSports.map((sport) => (
                    sport.leagues && sport.leagues.length > 0 ? (
                      <Box key={sport.name} sx={{ px:1, py:0.5 }}>
                        <ListItem disablePadding>
                          <ListItemText primary={sport.name} sx={{ pl:1, fontWeight:700 }} />
                        </ListItem>
                        {sport.leagues.map((league) => (
                          <ListItem key={league.path} disablePadding>
                            <ListItemButton sx={{ pl:4 }} onClick={() => handleDrawerItemClick(league.path)}>
                              <ListItemText primary={league.name} />
                            </ListItemButton>
                          </ListItem>
                        ))}
                      </Box>
                    ) : (
                      <ListItem key={sport.name} disablePadding>
                        <ListItemButton onClick={() => handleDrawerItemClick(sport.path)}>
                          <ListItemText primary={sport.name} />
                        </ListItemButton>
                      </ListItem>
                    )
                  ))}
                </List>
                <Divider sx={{ my:1 }} />
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
            <Tabs value={currentTab === -1 ? false : currentTab} onChange={(e,v) => handleTabChange(e as any, v as number)} textColor="primary" indicatorColor="primary">
              {inSeasonSports.map((sport) => (
                sport.leagues && sport.leagues.length > 0 ? (
                  <Tab key={sport.name} label={sport.name} onMouseDown={() => setSuppressNextChange(true)} onClick={(e) => { setAnchorEl(e.currentTarget as HTMLElement); setAnchorSport(sport.name); }} />
                  ) : (
                  <Tab key={sport.name} label={sport.name} onClick={() => sport.path && navigate(sport.path)} />
                )
              ))}
              {offSeasonSports.length > 0 && (
                <Button color="inherit" disableRipple className={styles.moreButton} onClick={handleMoreClick}>More</Button>
              )}
            </Tabs>

            {/* Off-season menu (when anchor is set but no sport-specific dropdown active) */}
            <Menu anchorEl={anchorEl} open={Boolean(anchorEl) && !anchorSport} onClose={handleClose}>
              {offSeasonSports.map((sport) => (
                <MenuItem key={sport.name} onClick={() => handleMenuItemClick(sport.path)}>{sport.name}</MenuItem>
              ))}
            </Menu>

            {/* League dropdown for sports with leagues */}
            <Menu anchorEl={anchorEl} open={Boolean(anchorEl) && Boolean(anchorSport)} onClose={handleClose}>
              {anchorSport && (() => {
                const sport = inSeasonSports.find((s) => s.name === anchorSport);
                if (!sport || !sport.leagues) return null;
                return sport.leagues.map((league) => (
                  <MenuItem key={league.path} onClick={() => handleMenuItemClick(league.path)}>{league.name}</MenuItem>
                ));
              })()}
            </Menu>
          </>
        )}
      </Box>

      {!isMobile && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, ml:2 }}>
          <Button color="inherit" disableRipple sx={{ minHeight:48, textTransform:'none', fontWeight:500 }} onClick={() => navigate('/feature-requests')}>Feature Requests</Button>
        </Box>
      )}

      {isMobile && (
        <Button
          variant="outlined"
          color="inherit"
          disableRipple
          aria-label="feature-requests"
          onClick={() => navigate('/feature-requests')}
          sx={{
            ml: 1,
            mt: 1,
            mb: 1,
            mr: 1,
            textTransform: 'none',
            fontWeight: 600,
            borderRadius: 2,
            px: 2,
            color: '#333',
            borderColor: '#e0e0e0',
            bgcolor: 'transparent',
            '&:hover': {
              bgcolor: '#f5f5f5',
              borderColor: '#bdbdbd',
            },
          }}
        >
          FEATURE REQUESTS
        </Button>
      )}
      
    </Box>
  );
};

export default TabsNavigation;