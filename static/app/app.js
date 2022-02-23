const {mount, Component, whenReady} = owl;
import { rpc } from "../core/rpc.js";
import {Header} from "../components/header/header.js"

class EcommerceRoot extends Component{

}

EcommerceRoot.template = "App";
EcommerceRoot.components = { Header }

async function setup () {
  const templates = await rpc("/loadqweb", {});
  const env = {};
  mount(EcommerceRoot, document.body, {templates, env});
}

whenReady(setup);