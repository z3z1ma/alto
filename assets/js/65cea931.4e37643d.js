"use strict";(self.webpackChunkalto_docs=self.webpackChunkalto_docs||[]).push([[293],{3905:(e,t,r)=>{r.d(t,{Zo:()=>p,kt:()=>f});var n=r(7294);function a(e,t,r){return t in e?Object.defineProperty(e,t,{value:r,enumerable:!0,configurable:!0,writable:!0}):e[t]=r,e}function o(e,t){var r=Object.keys(e);if(Object.getOwnPropertySymbols){var n=Object.getOwnPropertySymbols(e);t&&(n=n.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),r.push.apply(r,n)}return r}function i(e){for(var t=1;t<arguments.length;t++){var r=null!=arguments[t]?arguments[t]:{};t%2?o(Object(r),!0).forEach((function(t){a(e,t,r[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(r)):o(Object(r)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(r,t))}))}return e}function c(e,t){if(null==e)return{};var r,n,a=function(e,t){if(null==e)return{};var r,n,a={},o=Object.keys(e);for(n=0;n<o.length;n++)r=o[n],t.indexOf(r)>=0||(a[r]=e[r]);return a}(e,t);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);for(n=0;n<o.length;n++)r=o[n],t.indexOf(r)>=0||Object.prototype.propertyIsEnumerable.call(e,r)&&(a[r]=e[r])}return a}var s=n.createContext({}),l=function(e){var t=n.useContext(s),r=t;return e&&(r="function"==typeof e?e(t):i(i({},t),e)),r},p=function(e){var t=l(e.components);return n.createElement(s.Provider,{value:t},e.children)},m="mdxType",u={inlineCode:"code",wrapper:function(e){var t=e.children;return n.createElement(n.Fragment,{},t)}},d=n.forwardRef((function(e,t){var r=e.components,a=e.mdxType,o=e.originalType,s=e.parentName,p=c(e,["components","mdxType","originalType","parentName"]),m=l(r),d=a,f=m["".concat(s,".").concat(d)]||m[d]||u[d]||o;return r?n.createElement(f,i(i({ref:t},p),{},{components:r})):n.createElement(f,i({ref:t},p))}));function f(e,t){var r=arguments,a=t&&t.mdxType;if("string"==typeof e||a){var o=r.length,i=new Array(o);i[0]=d;var c={};for(var s in t)hasOwnProperty.call(t,s)&&(c[s]=t[s]);c.originalType=e,c[m]="string"==typeof e?e:a,i[1]=c;for(var l=2;l<o;l++)i[l]=r[l];return n.createElement.apply(null,i)}return n.createElement.apply(null,r)}d.displayName="MDXCreateElement"},7464:(e,t,r)=>{r.d(t,{Z:()=>h});var n=r(7294),a=r(6010),o=r(3438),i=r(9960),c=r(3919),s=r(5999);const l={cardContainer:"cardContainer_S8oU",cardTitle:"cardTitle_HoSo",cardDescription:"cardDescription_c27F"};function p(e){let{href:t,children:r}=e;return n.createElement(i.Z,{href:t,className:(0,a.Z)("card padding--lg",l.cardContainer)},r)}function m(e){let{href:t,icon:r,title:o,description:i,logo:c}=e;return n.createElement(p,{href:t},n.createElement("div",{style:{position:"relative"}},n.createElement("h2",{className:(0,a.Z)("text--truncate",l.cardTitle),title:o},r," ",o),c&&n.createElement("img",{src:c,style:{position:"absolute",top:-10,right:-10,width:"75px"}}),i&&n.createElement("p",{className:(0,a.Z)("text--truncate",l.cardDescription),title:i},i)))}function u(e){let{item:t}=e;const r=(0,o.Wl)(t);return r?n.createElement(m,{href:r,icon:"\ud83d\uddc3\ufe0f",title:t.label,description:(0,s.I)({message:"{count} items",id:"theme.docs.DocCard.categoryDescription",description:"The default description for a category card in the generated index about how many items this category includes"},{count:t.items.length})}):null}function d(e){let{item:t}=e;const r=(0,c.Z)(t.href)?"\ud83d\udcc4\ufe0f":"\ud83d\udd17",a=(0,o.xz)(t.docId??void 0);return n.createElement(m,{href:t.href,icon:r,title:t.label,description:a?.description??t.description,logo:t.logo})}function f(e){let{item:t}=e;switch(t.type){case"link":return n.createElement(d,{item:t});case"category":return n.createElement(u,{item:t});default:throw new Error(`unknown item type ${JSON.stringify(t)}`)}}function g(e){let{className:t}=e;const r=(0,o.jA)();return n.createElement(y,{items:r.items,className:t})}function y(e){const{items:t,className:r}=e;if(!t)return n.createElement(g,e);const i=(0,o.MN)(t);return n.createElement("section",{className:(0,a.Z)("row",r)},i.map(((e,t)=>n.createElement("article",{key:t,className:"col col--6 margin-bottom--lg"},n.createElement(f,{item:e})))))}const h=function(e){const[t,r]=(0,n.useState)([]),[a,o]=(0,n.useState)([]),[i,c]=(0,n.useState)("");return(0,n.useEffect)((()=>{(async()=>{const t=await fetch("https://raw.githubusercontent.com/meltano/hub/main/_data/default_variants.yml"),n=await t.text(),a={};var i=!1;for(const r of n.split("\n"))if(r.startsWith(e.type+":"))i=!0;else if(r.startsWith("  ")&&r.includes(":")&&i){const[e,t]=r.split(":",2);a[e.trim()]=t.trim()}else i=!1;r(a),o(a)})()}),[]),n.createElement("div",null,n.createElement("input",{type:"text",placeholder:`Search for ${e.type}...`,value:i,onChange:function(e){const r=e.target.value.toLowerCase(),n={};for(const[a,o]of Object.entries(t))a.toLowerCase().includes(r)&&(n[a]=o);o(n),c(r)}}),n.createElement("br",null),n.createElement("br",null),n.createElement(y,{items:Object.keys(a).map((r=>({type:"link",label:r,description:`maintainer: ${t[r]}`,href:`https://hub.meltano.com/${e.type}/${r}--${t[r]}/`,logo:`https://raw.githubusercontent.com/meltano/hub/main/static/assets/logos/${e.type}/${r.replace("tap-airbyte-wrapper","airbyte").replace("tap-rest-api-msdk","restapi").replace("tap-rickandmorty","rick-and-morty").replace("tap-decentraland-api","decentraland").replace("tap-decentraland-thegraph","decentraland").replace("tap-s3-csv","s3-csv").replace("tap-s3","s3-csv").replace("target-s3-csv","pipelinewise-s3-csv").replace("target-miso","misoai").replace("singer-","").replace("tap-","").replace("target-","")}.png`})))}))}},504:(e,t,r)=>{r.r(t),r.d(t,{assets:()=>l,contentTitle:()=>c,default:()=>d,frontMatter:()=>i,metadata:()=>s,toc:()=>p});var n=r(7462),a=(r(7294),r(3905)),o=r(7464);const i={},c="Target Index",s={unversionedId:"integrations/targets",id:"integrations/targets",title:"Target Index",description:"The following is a list of targets curated by the community. Targets are data loaders. The search bar will filter",source:"@site/docs/integrations/targets.mdx",sourceDirName:"integrations",slug:"/integrations/targets",permalink:"/alto/docs/integrations/targets",draft:!1,editUrl:"https://github.com/z3z1ma/alto/tree/main/docs/docs/integrations/targets.mdx",tags:[],version:"current",frontMatter:{},sidebar:"integrationsSidebar",previous:{title:"Tap Index",permalink:"/alto/docs/integrations/taps"}},l={},p=[],m={toc:p},u="wrapper";function d(e){let{components:t,...r}=e;return(0,a.kt)(u,(0,n.Z)({},m,r,{components:t,mdxType:"MDXLayout"}),(0,a.kt)("h1",{id:"target-index"},"Target Index"),(0,a.kt)("admonition",{type:"info"},(0,a.kt)("p",{parentName:"admonition"},"The following is a list of targets curated by the community. Targets are ",(0,a.kt)("strong",{parentName:"p"},"data loaders"),". The search bar will filter\nin realtime as you type. All links go to Meltano Hub where you can find more information as well as configuration settings.")),(0,a.kt)("hr",null),(0,a.kt)(o.Z,{type:"loaders",mdxType:"PluginIndex"}))}d.isMDXComponent=!0}}]);