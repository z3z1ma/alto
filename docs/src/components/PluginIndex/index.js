import React, { useState, useEffect } from 'react';
import DocCardList from '@docusaurus/theme-classic/lib/theme/DocCardList';

function PluginIndex(props) {
  const [data, setData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      const response = await fetch('https://raw.githubusercontent.com/meltano/hub/main/_data/default_variants.yml');
      const textData = await response.text();
      const jsonData = {};
      var inSection = false;
      for (const line of textData.split('\n')) {
        if (line.startsWith(props.type + ':')) {
          inSection = true;
        } else if (line.startsWith('  ') && line.includes(':') && inSection) {
          const [key, value] = line.split(':', 2);
          jsonData[key.trim()] = value.trim();
        } else {
          inSection = false;
        }
      }
      setData(jsonData);
      setFilteredData(jsonData);
    };
    fetchData();
  }, []);

  function handleInputChange(event) {
    const searchQuery = event.target.value.toLowerCase();
    const filteredData = {};
    for (const [key, value] of Object.entries(data)) {
      if (key.toLowerCase().includes(searchQuery)) {
        filteredData[key] = value;
      }
    }
    setFilteredData(filteredData);
    setSearchQuery(searchQuery);
  }

  // Render the component using the fetched data
  return (
    <div>
      <input
        type="text"
        placeholder={`Search for ${props.type}...`}
        value={searchQuery}
        onChange={handleInputChange}
      />
      <br />
      <br />
      <DocCardList items={Object.keys(filteredData).map((key) => ({
        type: 'link',
        label: key,
        description: `maintainer: ${data[key]}`,
        href: `https://hub.meltano.com/${props.type}/${key}--${data[key]}/`,
        logo: `https://raw.githubusercontent.com/meltano/hub/main/static/assets/logos/${props.type}/${
          key
          // Overrides for deviants
          .replace('tap-airbyte-wrapper', 'airbyte')
          .replace('tap-rest-api-msdk', 'restapi')
          .replace('tap-rickandmorty', 'rick-and-morty')
          .replace('tap-decentraland-api', 'decentraland')
          .replace('tap-decentraland-thegraph', 'decentraland')
          .replace('tap-s3-csv', 's3-csv')
          .replace('tap-s3', 's3-csv')
          .replace('target-s3-csv', 'pipelinewise-s3-csv')
          .replace('target-miso', 'misoai')
          .replace('singer-', '')
          // Non-deviants
          .replace('tap-', '')
          .replace('target-', '')}.png`,
      }))} />
    </div>
  );
}

export default PluginIndex;
