import React, { useState, useEffect } from 'react';

function PluginIndex(props) {
  const [data, setData] = useState([]);

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
    };

    fetchData();
  }, []);

  // Render the component using the fetched data
  return (
    <div>
      {Object.keys(data).map((key) => (
        <div key={key}>
          <p><a href={`https://hub.meltano.com/${props.type}/${key}--${data[key]}/`} target="_blank" rel="noopener">{key}</a> (default variant: {data[key]})</p>
        </div>
      ))}
    </div>
  );
}

export default PluginIndex;
