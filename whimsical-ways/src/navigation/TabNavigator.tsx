import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text, StyleSheet } from 'react-native';
import { HomeScreen } from '../screens/HomeScreen';
import { QuestScreen } from '../screens/QuestScreen';
import { PolaroidsScreen } from '../screens/PolaroidsScreen';
import { LeaderboardScreen } from '../screens/LeaderboardScreen';
import { ProfileScreen } from '../screens/ProfileScreen';
import { colors, typography } from '../theme';

const Tab = createBottomTabNavigator();

// Simple text-based tab icons (replace with proper icons later)
function TabIcon({ label, focused }: { label: string; focused: boolean }) {
  const icons: Record<string, string> = {
    Home: '\u2302',       // house
    Quests: '\u2694',     // swords (quest)
    Polaroids: '\u25A3',  // square (photo)
    Board: '\u2691',      // flag (leaderboard)
    Profile: '\u263A',    // smiley
  };

  return (
    <Text style={[styles.icon, focused && styles.iconFocused]}>
      {icons[label] || label.charAt(0)}
    </Text>
  );
}

export function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: styles.tabBar,
        tabBarActiveTintColor: colors.pinkAccent,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: styles.tabLabel,
        tabBarIcon: ({ focused }) => (
          <TabIcon label={route.name} focused={focused} />
        ),
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Quests" component={QuestScreen} />
      <Tab.Screen name="Polaroids" component={PolaroidsScreen} />
      <Tab.Screen name="Board" component={LeaderboardScreen} options={{ title: 'Friends' }} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: colors.white,
    borderTopWidth: 0,
    elevation: 8,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 1,
    shadowRadius: 12,
    height: 85,
    paddingBottom: 20,
    paddingTop: 8,
  },
  tabLabel: {
    fontSize: typography.sizes.xs,
    fontWeight: '600',
  },
  icon: {
    fontSize: 22,
    color: colors.textMuted,
  },
  iconFocused: {
    color: colors.pinkAccent,
  },
});
