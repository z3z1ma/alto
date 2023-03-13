"use strict";(self.webpackChunkalto_docs=self.webpackChunkalto_docs||[]).push([[428],{3905:(e,t,a)=>{a.d(t,{Zo:()=>m,kt:()=>y});var n=a(7294);function r(e,t,a){return t in e?Object.defineProperty(e,t,{value:a,enumerable:!0,configurable:!0,writable:!0}):e[t]=a,e}function o(e,t){var a=Object.keys(e);if(Object.getOwnPropertySymbols){var n=Object.getOwnPropertySymbols(e);t&&(n=n.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),a.push.apply(a,n)}return a}function l(e){for(var t=1;t<arguments.length;t++){var a=null!=arguments[t]?arguments[t]:{};t%2?o(Object(a),!0).forEach((function(t){r(e,t,a[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(a)):o(Object(a)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(a,t))}))}return e}function i(e,t){if(null==e)return{};var a,n,r=function(e,t){if(null==e)return{};var a,n,r={},o=Object.keys(e);for(n=0;n<o.length;n++)a=o[n],t.indexOf(a)>=0||(r[a]=e[a]);return r}(e,t);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);for(n=0;n<o.length;n++)a=o[n],t.indexOf(a)>=0||Object.prototype.propertyIsEnumerable.call(e,a)&&(r[a]=e[a])}return r}var s=n.createContext({}),p=function(e){var t=n.useContext(s),a=t;return e&&(a="function"==typeof e?e(t):l(l({},t),e)),a},m=function(e){var t=p(e.components);return n.createElement(s.Provider,{value:t},e.children)},c="mdxType",d={inlineCode:"code",wrapper:function(e){var t=e.children;return n.createElement(n.Fragment,{},t)}},u=n.forwardRef((function(e,t){var a=e.components,r=e.mdxType,o=e.originalType,s=e.parentName,m=i(e,["components","mdxType","originalType","parentName"]),c=p(a),u=r,y=c["".concat(s,".").concat(u)]||c[u]||d[u]||o;return a?n.createElement(y,l(l({ref:t},m),{},{components:a})):n.createElement(y,l({ref:t},m))}));function y(e,t){var a=arguments,r=t&&t.mdxType;if("string"==typeof e||r){var o=a.length,l=new Array(o);l[0]=u;var i={};for(var s in t)hasOwnProperty.call(t,s)&&(i[s]=t[s]);i.originalType=e,i[c]="string"==typeof e?e:r,l[1]=i;for(var p=2;p<o;p++)l[p]=a[p];return n.createElement.apply(null,l)}return n.createElement.apply(null,a)}u.displayName="MDXCreateElement"},493:(e,t,a)=>{a.r(t),a.d(t,{assets:()=>s,contentTitle:()=>l,default:()=>d,frontMatter:()=>o,metadata:()=>i,toc:()=>p});var n=a(7462),r=(a(7294),a(3905));const o={sidebar_position:2},l="State Management",i={unversionedId:"tutorial-advanced/state-management",id:"tutorial-advanced/state-management",title:"State Management",description:'Alto never destroys prior state files. We leave it to the user to decide where, when, and how to purge state files. The current state can be found in the state directory of your remote storage (we refer to the latest state as the "active state"). Furthermore, state is automatically partitioned by environment. For example, if you have a tap named my-tap pushing data to my-target and you have an environment named dev-alex, the state file for that tap will be located at state/dev-alex/my-tap-to-my-target.json. Historical state files will be preserved at state/dev-alex/my-tap-to-my-target..json.',source:"@site/docs/tutorial-advanced/state-management.md",sourceDirName:"tutorial-advanced",slug:"/tutorial-advanced/state-management",permalink:"/alto/docs/tutorial-advanced/state-management",draft:!1,editUrl:"https://github.com/z3z1ma/alto/tree/main/docs/docs/tutorial-advanced/state-management.md",tags:[],version:"current",sidebarPosition:2,frontMatter:{sidebar_position:2}},s={},p=[{value:"Purging All State Files",id:"purging-all-state-files",level:2}],m={toc:p},c="wrapper";function d(e){let{components:t,...a}=e;return(0,r.kt)(c,(0,n.Z)({},m,a,{components:t,mdxType:"MDXLayout"}),(0,r.kt)("h1",{id:"state-management"},"State Management"),(0,r.kt)("p",null,"Alto never destroys prior state files. We leave it to the user to decide where, when, and how to purge state files. The current state can be found in the ",(0,r.kt)("inlineCode",{parentName:"p"},"state"),' directory of your remote storage (we refer to the latest state as the "active state"). Furthermore, state is automatically partitioned by environment. For example, if you have a tap named ',(0,r.kt)("inlineCode",{parentName:"p"},"my-tap")," pushing data to ",(0,r.kt)("inlineCode",{parentName:"p"},"my-target")," and you have an environment named ",(0,r.kt)("inlineCode",{parentName:"p"},"dev-alex"),", the state file for that tap will be located at ",(0,r.kt)("inlineCode",{parentName:"p"},"state/dev-alex/my-tap-to-my-target.json"),". Historical state files will be preserved at ",(0,r.kt)("inlineCode",{parentName:"p"},"state/dev-alex/my-tap-to-my-target.{timestamp}.json"),"."),(0,r.kt)("p",null,"It can be reset by running the ",(0,r.kt)("inlineCode",{parentName:"p"},"alto clean my-tap:my-target")," command."),(0,r.kt)("p",null,"Following the example above, if you wanted to clear the active state, you would run the following command:"),(0,r.kt)("pre",null,(0,r.kt)("code",{parentName:"pre",className:"language-bash"},"alto clean my-tap:my-target\n")),(0,r.kt)("p",null,"This will delete the state file for the tap named ",(0,r.kt)("inlineCode",{parentName:"p"},"my-tap")," to the target ",(0,r.kt)("inlineCode",{parentName:"p"},"my-target")," in the ",(0,r.kt)("inlineCode",{parentName:"p"},"state")," directory of your remote storage."),(0,r.kt)("p",null,"Extending the previous example in a more functional way, if you wanted to clear the active state and then run the tap to target, you would run the following command:"),(0,r.kt)("pre",null,(0,r.kt)("code",{parentName:"pre",className:"language-bash"},"alto clean my-tap:my-target ; alto my-tap:my-target\n")),(0,r.kt)("p",null,'This would result in a "full refresh" of the tap to target.'),(0,r.kt)("h2",{id:"purging-all-state-files"},"Purging All State Files"),(0,r.kt)("p",null,"If you want to purge all active state files, you can run the following command:"),(0,r.kt)("pre",null,(0,r.kt)("code",{parentName:"pre",className:"language-bash"},"alto clean state\n")),(0,r.kt)("admonition",{title:"Danger",type:"danger"},(0,r.kt)("p",{parentName:"admonition"},"This will delete all active state files in the ",(0,r.kt)("inlineCode",{parentName:"p"},"state")," directory of your remote storage. (Historical state files will be preserved.)")))}d.isMDXComponent=!0}}]);