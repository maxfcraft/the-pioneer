import React from 'react';
import { View, Text, StyleSheet, Image } from 'react-native';
import { colors, spacing, typography, borderRadius } from '../../theme';
import { formatSteps, formatCoins } from '../../utils/coins';

interface Props {
  rank: number;
  displayName: string;
  avatarUrl: string | null;
  value: number;
  type: 'steps' | 'coins';
  isCurrentUser?: boolean;
}

const rankColors: Record<number, string> = {
  1: '#D4A574', // gold
  2: '#C0C0C0', // silver
  3: '#CD7F32', // bronze
};

export function LeaderboardEntry({ rank, displayName, avatarUrl, value, type, isCurrentUser }: Props) {
  return (
    <View style={[styles.row, isCurrentUser && styles.currentUser]}>
      <Text style={[styles.rank, rank <= 3 && { color: rankColors[rank] }]}>
        #{rank}
      </Text>

      <View style={styles.avatar}>
        {avatarUrl ? (
          <Image source={{ uri: avatarUrl }} style={styles.avatarImage} />
        ) : (
          <View style={styles.avatarPlaceholder}>
            <Text style={styles.avatarText}>{displayName.charAt(0).toUpperCase()}</Text>
          </View>
        )}
      </View>

      <Text style={styles.name} numberOfLines={1}>
        {displayName}
        {isCurrentUser ? ' (you)' : ''}
      </Text>

      <Text style={styles.value}>
        {type === 'steps' ? formatSteps(value) : formatCoins(value)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.pinkLight,
  },
  currentUser: {
    backgroundColor: colors.pinkLight,
    borderRadius: borderRadius.md,
    borderBottomWidth: 0,
    marginVertical: spacing.xs,
  },
  rank: {
    fontSize: typography.sizes.md,
    fontWeight: '700',
    color: colors.textLight,
    width: 36,
  },
  avatar: {
    marginRight: spacing.md,
  },
  avatarImage: {
    width: 36,
    height: 36,
    borderRadius: 18,
  },
  avatarPlaceholder: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.pinkDark,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: colors.white,
    fontWeight: '700',
    fontSize: typography.sizes.md,
  },
  name: {
    flex: 1,
    fontSize: typography.sizes.md,
    color: colors.text,
    fontWeight: '500',
  },
  value: {
    fontSize: typography.sizes.md,
    fontWeight: '700',
    color: colors.gold,
  },
});
