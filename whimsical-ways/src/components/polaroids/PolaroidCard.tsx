import React from 'react';
import { View, Image, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { BlurView } from 'expo-blur';
import { colors, spacing, borderRadius, typography } from '../../theme';
import type { Photo } from '../../types';
import { formatSteps } from '../../utils/coins';

interface Props {
  photo: Photo;
  stepsRemaining?: number;
  onPress?: () => void;
}

export function PolaroidCard({ photo, stepsRemaining = 0, onPress }: Props) {
  return (
    <TouchableOpacity
      style={styles.frame}
      onPress={onPress}
      activeOpacity={0.85}
      disabled={!onPress}
    >
      <View style={styles.imageContainer}>
        <Image source={{ uri: photo.localUri }} style={styles.image} />

        {!photo.isRevealed && (
          <BlurView intensity={95} style={styles.blurOverlay} tint="light">
            <Text style={styles.lockIcon}>&#x1F512;</Text>
            <Text style={styles.lockText}>Developing...</Text>
            {stepsRemaining > 0 && (
              <Text style={styles.stepsText}>
                {formatSteps(stepsRemaining)} steps to reveal
              </Text>
            )}
          </BlurView>
        )}

        {/* Coquette warm filter overlay for revealed photos */}
        {photo.isRevealed && <View style={styles.coquetteFilter} />}
      </View>

      <View style={styles.caption}>
        <Text style={styles.dateText}>
          {photo.isRevealed ? 'Revealed' : 'Locked'}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  frame: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.sm,
    padding: spacing.sm,
    paddingBottom: spacing.lg,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 8,
    elevation: 3,
    // Slight random rotation for Polaroid feel
    transform: [{ rotate: '-1deg' }],
  },
  imageContainer: {
    borderRadius: borderRadius.sm,
    overflow: 'hidden',
    aspectRatio: 1,
  },
  image: {
    width: '100%',
    height: '100%',
  },
  blurOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
  },
  lockIcon: {
    fontSize: 32,
    marginBottom: spacing.xs,
  },
  lockText: {
    fontSize: typography.sizes.md,
    fontWeight: '600',
    color: colors.text,
  },
  stepsText: {
    fontSize: typography.sizes.xs,
    color: colors.textLight,
    marginTop: spacing.xs,
  },
  coquetteFilter: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(255, 200, 180, 0.12)',
  },
  caption: {
    marginTop: spacing.sm,
    alignItems: 'center',
  },
  dateText: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    fontWeight: '500',
  },
});
