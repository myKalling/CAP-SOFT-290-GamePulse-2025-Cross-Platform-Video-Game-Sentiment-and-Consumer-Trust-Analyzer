import React from 'react';
import { Text, View } from 'react-native';

import EmailLink from './themed-email-link';

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
          <Text style={{ marginRight: 8 }}>•</Text>
          <Text>{listItem.item}</Text>
          {listItem.link ? (
            <EmailLink recipient={listItem.link.replace(/^mailto:/, '')} />
          ) : null}
        </View>
      ))}
    </View>
  );
}
