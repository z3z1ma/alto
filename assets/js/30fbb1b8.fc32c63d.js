"use strict";(self.webpackChunkalto_docs=self.webpackChunkalto_docs||[]).push([[945],{3905:(e,t,a)=>{a.d(t,{Zo:()=>l,kt:()=>g});var r=a(7294);function n(e,t,a){return t in e?Object.defineProperty(e,t,{value:a,enumerable:!0,configurable:!0,writable:!0}):e[t]=a,e}function o(e,t){var a=Object.keys(e);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(e);t&&(r=r.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),a.push.apply(a,r)}return a}function i(e){for(var t=1;t<arguments.length;t++){var a=null!=arguments[t]?arguments[t]:{};t%2?o(Object(a),!0).forEach((function(t){n(e,t,a[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(a)):o(Object(a)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(a,t))}))}return e}function s(e,t){if(null==e)return{};var a,r,n=function(e,t){if(null==e)return{};var a,r,n={},o=Object.keys(e);for(r=0;r<o.length;r++)a=o[r],t.indexOf(a)>=0||(n[a]=e[a]);return n}(e,t);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);for(r=0;r<o.length;r++)a=o[r],t.indexOf(a)>=0||Object.prototype.propertyIsEnumerable.call(e,a)&&(n[a]=e[a])}return n}var c=r.createContext({}),p=function(e){var t=r.useContext(c),a=t;return e&&(a="function"==typeof e?e(t):i(i({},t),e)),a},l=function(e){var t=p(e.components);return r.createElement(c.Provider,{value:t},e.children)},d="mdxType",u={inlineCode:"code",wrapper:function(e){var t=e.children;return r.createElement(r.Fragment,{},t)}},f=r.forwardRef((function(e,t){var a=e.components,n=e.mdxType,o=e.originalType,c=e.parentName,l=s(e,["components","mdxType","originalType","parentName"]),d=p(a),f=n,g=d["".concat(c,".").concat(f)]||d[f]||u[f]||o;return a?r.createElement(g,i(i({ref:t},l),{},{components:a})):r.createElement(g,i({ref:t},l))}));function g(e,t){var a=arguments,n=t&&t.mdxType;if("string"==typeof e||n){var o=a.length,i=new Array(o);i[0]=f;var s={};for(var c in t)hasOwnProperty.call(t,c)&&(s[c]=t[c]);s.originalType=e,s[d]="string"==typeof e?e:n,i[1]=s;for(var p=2;p<o;p++)i[p]=a[p];return r.createElement.apply(null,i)}return r.createElement.apply(null,a)}f.displayName="MDXCreateElement"},4425:(e,t,a)=>{a.r(t),a.d(t,{assets:()=>c,contentTitle:()=>i,default:()=>u,frontMatter:()=>o,metadata:()=>s,toc:()=>p});var r=a(7462),n=(a(7294),a(3905));const o={},i="Overview",s={unversionedId:"integrations/intro",id:"integrations/intro",title:"Overview",description:"Integrations are based entirely on the Singer ecosystem. Singer is an open source specification for the interchange format between a data extractor and a data loader referred to as taps and targets respectively. Due to the open nature of the specification, there are many taps and targets available. The Singer ecosystem is a great place to start if you are looking for a way to extract data from a source or load data into a destination without writing any code. The best source for the available taps and targets is the Meltano Hub. The Meltano Hub is a community driven repository of Singer tap and target metadata. They expose metadata describing what configuration options are available for each tap and target and have a nice user interface. Outside of the Meltano Hub, GitHub is a great place to search for Singer taps and targets.",source:"@site/docs/integrations/intro.md",sourceDirName:"integrations",slug:"/integrations/intro",permalink:"/alto/docs/integrations/intro",draft:!1,editUrl:"https://github.com/z3z1ma/alto/tree/main/docs/docs/integrations/intro.md",tags:[],version:"current",frontMatter:{},sidebar:"integrationsSidebar",next:{title:"Tap Index",permalink:"/alto/docs/integrations/taps"}},c={},p=[],l={toc:p},d="wrapper";function u(e){let{components:t,...a}=e;return(0,n.kt)(d,(0,r.Z)({},l,a,{components:t,mdxType:"MDXLayout"}),(0,n.kt)("h1",{id:"overview"},"Overview"),(0,n.kt)("p",null,"Integrations are based entirely on the Singer ecosystem. ",(0,n.kt)("a",{parentName:"p",href:"https://singer.io"},"Singer")," is an open source ",(0,n.kt)("a",{parentName:"p",href:"https://github.com/singer-io/getting-started/blob/master/docs/SPEC.md"},"specification")," for the interchange format between a data extractor and a data loader referred to as ",(0,n.kt)("inlineCode",{parentName:"p"},"taps")," and ",(0,n.kt)("inlineCode",{parentName:"p"},"targets")," respectively. Due to the open nature of the specification, there are many taps and targets available. The Singer ecosystem is a great place to start if you are looking for a way to extract data from a source or load data into a destination without writing any code. The best source for the available taps and targets is the ",(0,n.kt)("a",{parentName:"p",href:"https://hub.meltano.com/"},"Meltano Hub"),". The Meltano Hub is a community driven repository of Singer tap and target metadata. They expose metadata describing what configuration options are available for each tap and target and have a nice user interface. Outside of the Meltano Hub, ",(0,n.kt)("a",{parentName:"p",href:"https://github.com/"},"GitHub")," is a great place to search for Singer taps and targets."),(0,n.kt)("p",null,"We expose an index of taps and targets from Meltano hub as a convenience in the following sections. Feel free to use this index get an idea of the available taps and targets."))}u.isMDXComponent=!0}}]);