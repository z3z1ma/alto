"use strict";(self.webpackChunkalto_docs=self.webpackChunkalto_docs||[]).push([[321],{3905:(e,t,n)=>{n.d(t,{Zo:()=>u,kt:()=>h});var a=n(7294);function r(e,t,n){return t in e?Object.defineProperty(e,t,{value:n,enumerable:!0,configurable:!0,writable:!0}):e[t]=n,e}function o(e,t){var n=Object.keys(e);if(Object.getOwnPropertySymbols){var a=Object.getOwnPropertySymbols(e);t&&(a=a.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),n.push.apply(n,a)}return n}function i(e){for(var t=1;t<arguments.length;t++){var n=null!=arguments[t]?arguments[t]:{};t%2?o(Object(n),!0).forEach((function(t){r(e,t,n[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(n)):o(Object(n)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(n,t))}))}return e}function l(e,t){if(null==e)return{};var n,a,r=function(e,t){if(null==e)return{};var n,a,r={},o=Object.keys(e);for(a=0;a<o.length;a++)n=o[a],t.indexOf(n)>=0||(r[n]=e[n]);return r}(e,t);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);for(a=0;a<o.length;a++)n=o[a],t.indexOf(n)>=0||Object.prototype.propertyIsEnumerable.call(e,n)&&(r[n]=e[n])}return r}var s=a.createContext({}),c=function(e){var t=a.useContext(s),n=t;return e&&(n="function"==typeof e?e(t):i(i({},t),e)),n},u=function(e){var t=c(e.components);return a.createElement(s.Provider,{value:t},e.children)},p="mdxType",d={inlineCode:"code",wrapper:function(e){var t=e.children;return a.createElement(a.Fragment,{},t)}},m=a.forwardRef((function(e,t){var n=e.components,r=e.mdxType,o=e.originalType,s=e.parentName,u=l(e,["components","mdxType","originalType","parentName"]),p=c(n),m=r,h=p["".concat(s,".").concat(m)]||p[m]||d[m]||o;return n?a.createElement(h,i(i({ref:t},u),{},{components:n})):a.createElement(h,i({ref:t},u))}));function h(e,t){var n=arguments,r=t&&t.mdxType;if("string"==typeof e||r){var o=n.length,i=new Array(o);i[0]=m;var l={};for(var s in t)hasOwnProperty.call(t,s)&&(l[s]=t[s]);l.originalType=e,l[p]="string"==typeof e?e:r,i[1]=l;for(var c=2;c<o;c++)i[c]=n[c];return a.createElement.apply(null,i)}return a.createElement.apply(null,n)}m.displayName="MDXCreateElement"},5162:(e,t,n)=>{n.d(t,{Z:()=>i});var a=n(7294),r=n(6010);const o={tabItem:"tabItem_Ymn6"};function i(e){let{children:t,hidden:n,className:i}=e;return a.createElement("div",{role:"tabpanel",className:(0,r.Z)(o.tabItem,i),hidden:n},t)}},4866:(e,t,n)=>{n.d(t,{Z:()=>k});var a=n(7462),r=n(7294),o=n(6010),i=n(2466),l=n(6550),s=n(1980),c=n(7392),u=n(12);function p(e){return function(e){return r.Children.map(e,(e=>{if((0,r.isValidElement)(e)&&"value"in e.props)return e;throw new Error(`Docusaurus error: Bad <Tabs> child <${"string"==typeof e.type?e.type:e.type.name}>: all children of the <Tabs> component should be <TabItem>, and every <TabItem> should have a unique "value" prop.`)}))}(e).map((e=>{let{props:{value:t,label:n,attributes:a,default:r}}=e;return{value:t,label:n,attributes:a,default:r}}))}function d(e){const{values:t,children:n}=e;return(0,r.useMemo)((()=>{const e=t??p(n);return function(e){const t=(0,c.l)(e,((e,t)=>e.value===t.value));if(t.length>0)throw new Error(`Docusaurus error: Duplicate values "${t.map((e=>e.value)).join(", ")}" found in <Tabs>. Every value needs to be unique.`)}(e),e}),[t,n])}function m(e){let{value:t,tabValues:n}=e;return n.some((e=>e.value===t))}function h(e){let{queryString:t=!1,groupId:n}=e;const a=(0,l.k6)(),o=function(e){let{queryString:t=!1,groupId:n}=e;if("string"==typeof t)return t;if(!1===t)return null;if(!0===t&&!n)throw new Error('Docusaurus error: The <Tabs> component groupId prop is required if queryString=true, because this value is used as the search param name. You can also provide an explicit value such as queryString="my-search-param".');return n??null}({queryString:t,groupId:n});return[(0,s._X)(o),(0,r.useCallback)((e=>{if(!o)return;const t=new URLSearchParams(a.location.search);t.set(o,e),a.replace({...a.location,search:t.toString()})}),[o,a])]}function f(e){const{defaultValue:t,queryString:n=!1,groupId:a}=e,o=d(e),[i,l]=(0,r.useState)((()=>function(e){let{defaultValue:t,tabValues:n}=e;if(0===n.length)throw new Error("Docusaurus error: the <Tabs> component requires at least one <TabItem> children component");if(t){if(!m({value:t,tabValues:n}))throw new Error(`Docusaurus error: The <Tabs> has a defaultValue "${t}" but none of its children has the corresponding value. Available values are: ${n.map((e=>e.value)).join(", ")}. If you intend to show no default tab, use defaultValue={null} instead.`);return t}const a=n.find((e=>e.default))??n[0];if(!a)throw new Error("Unexpected error: 0 tabValues");return a.value}({defaultValue:t,tabValues:o}))),[s,c]=h({queryString:n,groupId:a}),[p,f]=function(e){let{groupId:t}=e;const n=function(e){return e?`docusaurus.tab.${e}`:null}(t),[a,o]=(0,u.Nk)(n);return[a,(0,r.useCallback)((e=>{n&&o.set(e)}),[n,o])]}({groupId:a}),b=(()=>{const e=s??p;return m({value:e,tabValues:o})?e:null})();(0,r.useLayoutEffect)((()=>{b&&l(b)}),[b]);return{selectedValue:i,selectValue:(0,r.useCallback)((e=>{if(!m({value:e,tabValues:o}))throw new Error(`Can't select invalid tab value=${e}`);l(e),c(e),f(e)}),[c,f,o]),tabValues:o}}var b=n(2389);const g={tabList:"tabList__CuJ",tabItem:"tabItem_LNqP"};function v(e){let{className:t,block:n,selectedValue:l,selectValue:s,tabValues:c}=e;const u=[],{blockElementScrollPositionUntilNextRender:p}=(0,i.o5)(),d=e=>{const t=e.currentTarget,n=u.indexOf(t),a=c[n].value;a!==l&&(p(t),s(a))},m=e=>{let t=null;switch(e.key){case"Enter":d(e);break;case"ArrowRight":{const n=u.indexOf(e.currentTarget)+1;t=u[n]??u[0];break}case"ArrowLeft":{const n=u.indexOf(e.currentTarget)-1;t=u[n]??u[u.length-1];break}}t?.focus()};return r.createElement("ul",{role:"tablist","aria-orientation":"horizontal",className:(0,o.Z)("tabs",{"tabs--block":n},t)},c.map((e=>{let{value:t,label:n,attributes:i}=e;return r.createElement("li",(0,a.Z)({role:"tab",tabIndex:l===t?0:-1,"aria-selected":l===t,key:t,ref:e=>u.push(e),onKeyDown:m,onClick:d},i,{className:(0,o.Z)("tabs__item",g.tabItem,i?.className,{"tabs__item--active":l===t})}),n??t)})))}function y(e){let{lazy:t,children:n,selectedValue:a}=e;if(n=Array.isArray(n)?n:[n],t){const e=n.find((e=>e.props.value===a));return e?(0,r.cloneElement)(e,{className:"margin-top--md"}):null}return r.createElement("div",{className:"margin-top--md"},n.map(((e,t)=>(0,r.cloneElement)(e,{key:t,hidden:e.props.value!==a}))))}function _(e){const t=f(e);return r.createElement("div",{className:(0,o.Z)("tabs-container",g.tabList)},r.createElement(v,(0,a.Z)({},e,t)),r.createElement(y,(0,a.Z)({},e,t)))}function k(e){const t=(0,b.Z)();return r.createElement(_,(0,a.Z)({key:String(t)},e))}},5861:(e,t,n)=>{n.r(t),n.d(t,{assets:()=>u,contentTitle:()=>s,default:()=>h,frontMatter:()=>l,metadata:()=>c,toc:()=>p});var a=n(7462),r=(n(7294),n(3905)),o=n(4866),i=n(5162);const l={},s="Example Configuration",c={unversionedId:"tutorial-basics/example-configuration",id:"tutorial-basics/example-configuration",title:"Example Configuration",description:"What does a configuration file look like?",source:"@site/docs/tutorial-basics/example-configuration.mdx",sourceDirName:"tutorial-basics",slug:"/tutorial-basics/example-configuration",permalink:"/alto/docs/tutorial-basics/example-configuration",draft:!1,editUrl:"https://github.com/z3z1ma/alto/tree/main/docs/docs/tutorial-basics/example-configuration.mdx",tags:[],version:"current",frontMatter:{},sidebar:"tutorialSidebar",previous:{title:"Create a Project",permalink:"/alto/docs/tutorial-basics/create-a-project"},next:{title:"Environments",permalink:"/alto/docs/tutorial-basics/environments"}},u={},p=[{value:"What does a configuration file look like?",id:"what-does-a-configuration-file-look-like",level:2},{value:"TOML",id:"toml",level:4},{value:"YAML",id:"yaml",level:4},{value:"JSON",id:"json",level:4}],d={toc:p},m="wrapper";function h(e){let{components:t,...n}=e;return(0,r.kt)(m,(0,a.Z)({},d,n,{components:t,mdxType:"MDXLayout"}),(0,r.kt)("h1",{id:"example-configuration"},"Example Configuration"),(0,r.kt)("h2",{id:"what-does-a-configuration-file-look-like"},"What does a configuration file look like?"),(0,r.kt)("p",null,"This section contains examples of ",(0,r.kt)("inlineCode",{parentName:"p"},"alto")," configuration files. These examples are simply meant to help familiarize users. This is the exact configuration file that is generated when you run ",(0,r.kt)("inlineCode",{parentName:"p"},"alto init")," and all represent exactly the same thing. The choice of format is down to user preference though we recommend ",(0,r.kt)("inlineCode",{parentName:"p"},"toml"),". Once you understand the general structure, the next few sections will dive into the details of each field."),(0,r.kt)(o.Z,{mdxType:"Tabs"},(0,r.kt)(i.Z,{value:"toml",label:"TOML",default:!0,mdxType:"TabItem"},(0,r.kt)("h4",{id:"toml"},"TOML"),(0,r.kt)("p",null,"The advantage of ",(0,r.kt)("inlineCode",{parentName:"p"},"toml")," is that it is a bit more compact than ",(0,r.kt)("inlineCode",{parentName:"p"},"yaml"),". It is a ",(0,r.kt)("strong",{parentName:"p"},"great")," choice for smaller projects. It is also the only format that can colocate nested keys. This is useful for putting environment-specific ",(0,r.kt)("inlineCode",{parentName:"p"},"config")," in the same place."),(0,r.kt)("pre",null,(0,r.kt)("code",{parentName:"pre",className:"language-toml",metastring:'title="alto.toml"',title:'"alto.toml"'},'# Alto Starter Project\n\n# Anything in the default section is applied to all environments\n# you can have an arbitrary number of environments. The ALTO_ENV\n# environment variable is used to determine which environment to\n# layer over the default section.\n[default]\nproject_name = "{project}"\n# Enable builtin extensions or bring your own\nextensions = ["evidence"]\nload_path = "raw"\n# Set env vars that will be available to all plugins\nenvironment.STARTER_PROJECT = 1\n\n[default.taps.tap-carbon-intensity] # https://gitlab.com/meltano/tap-carbon-intensity\npip_url = "git+https://gitlab.com/meltano/tap-carbon-intensity.git#egg=tap_carbon_intensity"\nload_path = "carbon_intensity"\ncapabilities = ["state", "catalog"]\nselect = [\n  "*.*",\n  # PII hashing\n  "~*.dnoregion"\n]\n\n[default.taps.tap-bls] # https://hub.meltano.com/extractors/tap-bls\npip_url = "git+https://github.com/frasermarlow/tap-bls#egg=tap_bls"\ncapabilities = ["state", "catalog"]\nload_path = "bls"\nselect = ["JTU000000000000000JOR", "JTU000000000000000JOL"]\n# Configuring the tap\nconfig.startyear = "2019"\nconfig.endyear = "2020"\nconfig.calculations = "true"\nconfig.annualaverage = "false"\nconfig.aspects = "false"\nconfig.disable_collection = "true"\nconfig.update_state = "false"\nconfig.series_list_file_location = "./series.json"\n\n[default.targets.target-jsonl] # https://hub.meltano.com/loaders/target-singer-jsonl\npip_url = "target-jsonl==0.1.4"\n# this.load_path is a reference to the load_path of the tap\nconfig.destination_path = "@format output/{this.load_path}"\n\n[default.utilities.dlt] # https://github.com/dlt-hub/dlt\npip_url = "python-dlt[duckdb]>=0.2.0a25"\nenvironment.PEX_INHERIT_PATH = "fallback"\n\n# Example of a custom environment\n# This environment will be layered over the default section\n# and will override any values that are the same in both sections.\n# Dicts are merged, lists are appended. This would be active if\n# the environment variable ALTO_ENV=github_actions\n[github_actions]\nload_path = "cicd"\ntargets.target-jsonl.config.destination_path = "@format /github/workspace/output/{this.load_path}"\n'))),(0,r.kt)(i.Z,{value:"yaml",label:"YAML",mdxType:"TabItem"},(0,r.kt)("h4",{id:"yaml"},"YAML"),(0,r.kt)("p",null,"The advantage of using ",(0,r.kt)("inlineCode",{parentName:"p"},"yaml")," is that it is the most ubiquitous format. Many users will already be familiar with it. While ",(0,r.kt)("inlineCode",{parentName:"p"},"toml")," has the advantage of not requiring indentation, ",(0,r.kt)("inlineCode",{parentName:"p"},"yaml"),"'s indentation can prove a strength given larger configuration files."),(0,r.kt)("pre",null,(0,r.kt)("code",{parentName:"pre",className:"language-yaml",metastring:'title="alto.yaml"',title:'"alto.yaml"'},'# Alto Starter Project\n\n# Anything in the default section is applied to all environments\n# you can have an arbitrary number of environments. The ALTO_ENV\n# environment variable is used to determine which environment to\n# layer over the default section.\ndefault:\n  project_name: "{project}"\n  # Enable builtin extensions or bring your own\n  extensions:\n    - evidence\n  load_path: raw\n  environment:\n    # Set env vars that will be available to all plugins\n    STARTER_PROJECT: 1\n  taps:\n    tap-carbon-intensity: # https://gitlab.com/meltano/tap-carbon-intensity\n      pip_url: "git+https://gitlab.com/meltano/tap-carbon-intensity.git#egg=tap_carbon_intensity"\n      load_path: carbon_intensity\n      capabilities:\n        - state\n        - catalog\n      select:\n        - "*.*"\n        # PII hashing\n        - "~*.dnoregion"\n      config: {}\n    tap-bls: # https://hub.meltano.com/extractors/tap-bls\n      pip_url: "git+https://github.com/frasermarlow/tap-bls#egg=tap_bls"\n      capabilities:\n        - state\n        - catalog\n      load_path: bls\n      select:\n        - JTU000000000000000JOR\n        - JTU000000000000000JOL\n      config:\n        startyear: "2019"\n        endyear: "2020"\n        calculations: "true"\n        annualaverage: "false"\n        aspects: "false"\n        disable_collection: "true"\n        update_state: "false"\n        series_list_file_location: ./series.json\n  targets:\n    target-jsonl: # https://hub.meltano.com/loaders/target-singer-jsonl\n      pip_url: target-jsonl==0.1.4\n      config:\n        # this.load_path is a reference to the load_path of the tap\n        destination_path: "@format output/{this.load_path}"\n  utilities:\n    dlt:\n      pip_url: "python-dlt[duckdb]>=0.2.0a25"\n      environment:\n        # Set plugin specific env vars\n        PEX_INHERIT_PATH: fallback\n\n# Example of a custom environment\n# This environment will be layered over the default section\n# and will override any values that are the same in both sections.\n# Dicts are merged, lists are appended. This would be active if\n# the environment variable ALTO_ENV=github_actions\ngithub_actions:\n  load_path: cicd\n  targets:\n    target-jsonl:\n      config:\n        destination_path: "@format /github/workspace/output/{this.load_path}"\n'))),(0,r.kt)(i.Z,{value:"json",label:"JSON",mdxType:"TabItem"},(0,r.kt)("h4",{id:"json"},"JSON"),(0,r.kt)("p",null,"The primary value in json is that is extremely common and easy to generate programmatically. Most languages can do this without third party libs. The ",(0,r.kt)("inlineCode",{parentName:"p"},"alto dump")," command also produces json which alto iself can use."),(0,r.kt)("pre",null,(0,r.kt)("code",{parentName:"pre",className:"language-json",metastring:'title="alto.json"',title:'"alto.json"'},'{\n    "default": {\n        "project_name": "{project}",\n        "extensions": [\n            "evidence"\n        ],\n        "load_path": "raw",\n        "environment": {\n            "ALTO_STARTER_PROJECT": 1\n        },\n        "taps": {\n            "tap-carbon-intensity": {\n                "pip_url": "git+https://gitlab.com/meltano/tap-carbon-intensity.git#egg=tap_carbon_intensity",\n                "load_path": "carbon_intensity",\n                "capabilities": [\n                    "state",\n                    "catalog"\n                ],\n                "select": [\n                    "*.*",\n                    "~*.dnoregion"\n                ],\n                "config": { }\n            },\n            "tap-bls": {\n                "pip_url": "git+https://github.com/frasermarlow/tap-bls#egg=tap_bls",\n                "capabilities": [\n                    "state",\n                    "catalog"\n                ],\n                "load_path": "bls",\n                "select": [\n                    "JTU000000000000000JOR",\n                    "JTU000000000000000JOL"\n                ],\n                "config": {\n                    "startyear": "2019",\n                    "endyear": "2020",\n                    "calculations": "true",\n                    "annualaverage": "false",\n                    "aspects": "false",\n                    "disable_collection": "true",\n                    "update_state": "false",\n                    "series_list_file_location": "./series.json"\n                }\n            }\n        },\n        "targets": {\n            "target-jsonl": {\n                "pip_url": "target-jsonl==0.1.4",\n                "config": {\n                    "destination_path": "@format output/{this.load_path}"\n                }\n            }\n        },\n        "utilities": {\n            "dlt": {\n                "pip_url": "python-dlt[duckdb]>=0.2.0a25",\n                "environment": {\n                    "PEX_INHERIT_PATH": "fallback"\n                }\n            }\n        }\n    },\n    "github_actions": {\n        "load_path": "cicd",\n        "targets": {\n            "target-jsonl": {\n                "config": {\n                    "destination_path": "@format /github/workspace/output/{this.load_path}"\n                }\n            }\n        }\n    }\n}\n')))))}h.isMDXComponent=!0}}]);