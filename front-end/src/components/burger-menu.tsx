import { router, usePathname, type Href } from 'expo-router';
import { useState } from 'react';
import { Modal, Platform, Pressable, StyleSheet, Text } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Colors } from '@/constants/theme';

const MENU_ITEMS: { href: Href; label: string }[] = [
  { href: '/', label: 'Home Page' },
  { href: '/about', label: 'About' },
  { href: '/account', label: 'Account' },
  { href: '/games', label: 'Top 20 Games' },
];

const HEADER_BODY_HEIGHT = Platform.OS === 'ios' ? 44 : 56;

export function BurgerMenu() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const insets = useSafeAreaInsets();
  const menuTop = insets.top + HEADER_BODY_HEIGHT;

  return (
    <>
      <Pressable
        onPress={() => setOpen(true)}
        style={styles.button}
        accessibilityRole="button"
        accessibilityLabel="Open menu">
        <Text style={styles.icon}>☰</Text>
      </Pressable>

      <Modal
        visible={open}
        transparent
        animationType="fade"
        onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.overlay} onPress={() => setOpen(false)}>
          <Pressable
            style={[styles.dropdown, { top: menuTop, left: 8 }]}
            onPress={(event) => event.stopPropagation()}>
            {MENU_ITEMS.map((item) => {
              const selected = pathname === item.href;

              return (
                <Pressable
                  key={item.label}
                  onPress={() => {
                    setOpen(false);
                    router.push(item.href);
                  }}
                  style={[styles.item, selected && styles.itemSelected]}
                  accessibilityRole="link"
                  accessibilityState={{ selected }}>
                  <Text style={[styles.itemText, selected && styles.itemTextSelected]}>
                    {item.label}
                  </Text>
                </Pressable>
              );
            })}
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  button: {
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  icon: {
    fontSize: 24,
    color: Colors.tabs.background,
  },
  overlay: {
    flex: 1,
  },
  dropdown: {
    position: 'absolute',
    minWidth: 200,
    backgroundColor: Colors.tabs.background,
    borderRadius: 8,
    paddingVertical: 8,
    elevation: 6,
    shadowColor: '#000',
    shadowOpacity: 0.2,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
  },
  item: {
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  itemSelected: {
    backgroundColor: Colors.tabs.backgroundSelected,
  },
  itemText: {
    fontSize: 16,
    color: Colors.tabs.text,
  },
  itemTextSelected: {
    fontWeight: '700',
  },
});
