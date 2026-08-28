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
import IconButton from "@mui/material/IconButton";
import Avatar from "@mui/material/Avatar";
import styles from "./css/Navigation.module.css";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import { useNavigate, useLocation } from "react-router-dom";
import { sports } from "../configs/sportsConfig";
import { useAuth } from "../contexts/AuthContext";
import AuthDialog from "./AuthDialog";
import UpgradeDialog from "./UpgradeDialog";

const TabsNavigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const { user, logout, isPro, openBillingPortal } = useAuth();

  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [anchorSport, setAnchorSport] = React.useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [authDialogOpen, setAuthDialogOpen] = React.useState(false);
  const [upgradeDialogOpen, setUpgradeDialogOpen] = React.useState(false);
  const [userMenuAnchor, setUserMenuAnchor] = React.useState<null | HTMLElement>(null);

  const inSeasonSports = sports.filter((sport) => sport.inSeason);
  const offSeasonSports = sports.filter((sport) => !sport.inSeason);

  const isHome = location.pathname === "/";
  const sportTabIndex = inSeasonSports.findIndex((sport) => {
    if (location.pathname === sport.path) return true;
    if (sport.leagues && sport.leagues.some((l) => location.pathname === l.path)) return true;
    return false;
  });
  // HOME is index 0; sport tabs start at index 1
  const currentTab = isHome ? 0 : sportTabIndex === -1 ? false : sportTabIndex + 1;

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

    // Index 0 is always HOME
    if (newValue === 0) {
      navigate("/");
      return;
    }

    const sport = inSeasonSports[newValue - 1];
    if (!sport) return;

    const native = (event as React.SyntheticEvent)?.nativeEvent as any;

    if (sport.leagues && sport.leagues.length > 0) {
      if (native && (native.key === "Enter" || native.key === " ")) {
        navigate(sport.leagues[0].path);
      }
      return;
    }

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

  const handleUserMenuClose = () => setUserMenuAnchor(null);
  const handleLogout = () => {
    logout();
    handleUserMenuClose();
  };
  const handleUpgrade = () => {
    handleUserMenuClose();
    setUpgradeDialogOpen(true);
  };
  const handleManageBilling = () => {
    handleUserMenuClose();
    openBillingPortal();
  };

  const accountControls = user ? (
    <>
      <IconButton onClick={(e) => setUserMenuAnchor(e.currentTarget)} size="small">
        <Avatar sx={{ width: 32, height: 32, bgcolor: "primary.main", fontSize: 14 }}>
          {user.email[0].toUpperCase()}
        </Avatar>
      </IconButton>
      <Menu anchorEl={userMenuAnchor} open={Boolean(userMenuAnchor)} onClose={handleUserMenuClose}>
        <MenuItem disabled sx={{ opacity: "1 !important" }}>{user.email}</MenuItem>
        <Divider />
        {isPro ? (
          <MenuItem onClick={handleManageBilling}>Manage Billing</MenuItem>
        ) : (
          <MenuItem onClick={handleUpgrade}>Upgrade to Pro</MenuItem>
        )}
        <MenuItem onClick={handleLogout}>Log Out</MenuItem>
      </Menu>
    </>
  ) : (
    <Button color="inherit" disableRipple sx={{ textTransform: "none", fontWeight: 500 }} onClick={() => setAuthDialogOpen(true)}>
      Log In
    </Button>
  );

  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "transparent", display: "flex", alignItems: "center" }}>
      <Box sx={{ flex: 1 }}>
        {isMobile ? (
          <>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Button
                onClick={() => navigate('/')}
                disableRipple
                sx={{
                  ml: 1,
                  textTransform: 'none',
                  fontWeight: isHome ? 700 : 500,
                  color: isHome ? 'primary.main' : 'text.secondary',
                  borderBottom: '2px solid',
                  borderColor: isHome ? 'primary.main' : 'transparent',
                  borderRadius: 0,
                  py: 1.5,
                  px: 1.5,
                  minWidth: 0,
                }}
              >
                HOME
              </Button>
              <Button
                onClick={toggleDrawer(true)}
                disableRipple
                sx={{
                  textTransform: 'none',
                  fontWeight: 500,
                  color: 'text.secondary',
                  borderBottom: '2px solid transparent',
                  borderRadius: 0,
                  py: 1.5,
                  px: 1.5,
                  minWidth: 0,
                }}
              >
                MORE SPORTS
              </Button>
            </Box>
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
            <Tabs value={currentTab} onChange={(e,v) => handleTabChange(e as any, v as number)} textColor="primary" indicatorColor="primary">
              <Tab label="Home" onClick={() => navigate("/")} />
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml:2 }}>
          <Button color="inherit" disableRipple sx={{ minHeight:48, textTransform:'none', fontWeight:500 }} onClick={() => navigate('/feature-requests')}>Feature Requests</Button>
          {accountControls}
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

      {isMobile && (
        <Box sx={{ display: 'flex', alignItems: 'center', mr: 1 }}>
          {accountControls}
        </Box>
      )}

      <AuthDialog open={authDialogOpen} onClose={() => setAuthDialogOpen(false)} />
      <UpgradeDialog open={upgradeDialogOpen} onClose={() => setUpgradeDialogOpen(false)} />
    </Box>
  );
};

export default TabsNavigation;