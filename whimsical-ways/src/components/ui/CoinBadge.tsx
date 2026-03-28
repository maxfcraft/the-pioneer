import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, borderRadius, spacing, typography } from '../../theme';
import { formatCoins } from '../../utils/coins';

interface Props {
  coins: number;
  size?: 'sm' | 'md' | 'lg';
}

export function CoinBadge({ coins, size = 'md' }: Props) {
  const fontSize = size === 'sm' ? typography.sizes.sm : size === 'lg' ? typography.sizes.xl : typography.sizes.lg;

  return (
    <View style={[styles.container, size === 'lg' && styles.containerLg]}>
      <Text style={[styles.icon, { fontSize }]}>&#x2B50;</Text>
      <Text style={[styles.text, { fontSize }]}>{formatCoins(coins)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.goldLight,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
    borderRadius: borderRadius.round,
    gap: spacing.xs,
  },
  containerLg: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
  },
  icon: {
    color: colors.gold,
  },
  text: {
    color: colors.text,
    fontWeight: '700',
  },
});
