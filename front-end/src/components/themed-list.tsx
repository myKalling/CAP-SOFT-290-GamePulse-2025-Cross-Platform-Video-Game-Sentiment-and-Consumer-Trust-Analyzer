import React from 'react';
import { Text, View } from 'react-native';

import EmailLink from './themed-email-link';
import { ThemedText } from './themed-text';

interface ListItem {
  item: string;
  link?: string;
}

export default function ThemedList({ items }: { items: ListItem[] }) {

  return (
    <View style={{ flexDirection: 'column' }}>
      {items.map((listItem, index) => (
        // unicode bullet
        <View key={index} style={{ flexDirection: 'row', alignItems: 'center' }}>
          <ThemedText style={{ marginRight: 8 }}>•</ThemedText>
          <ThemedText>{listItem.item}</ThemedText>
          {listItem.link ? (
            <EmailLink recipient={listItem.link.replace(/^mailto:/, '')} />
          ) : null}
        </View>
      ))}
    </View>
  );
}
